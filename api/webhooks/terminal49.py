"""Terminal49 webhook handler."""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session

from models import get_db, Container, ContainerEvent
from integrations.terminal49_client import Terminal49Client
from config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/terminal49")
async def handle_terminal49_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_terminal49_signature: str = Header(None)
):
    """Handle Terminal49 container update webhooks."""
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify signature
        terminal49 = Terminal49Client()
        if not terminal49.verify_webhook_signature(body, x_terminal49_signature or ""):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse payload
        payload = await request.json()
        
        # Extract event data
        event_type = payload.get("type")
        data = payload.get("data", {})
        
        # Find container by tracking ID
        tracking_id = data.get("id")
        container = (
            db.query(Container)
            .filter(Container.terminal49_tracking_id == tracking_id)
            .first()
        )
        
        if not container:
            logger.warning(f"Container not found for tracking ID: {tracking_id}")
            return {"status": "ignored", "reason": "container not found"}
        
        # Create event record
        event = ContainerEvent(
            container_id=container.id,
            event_type=event_type,
            event_time=data.get("timestamp"),
            location=data.get("location"),
            description=data.get("description"),
            raw_data=payload,
        )
        db.add(event)
        
        # Update container status
        attributes = data.get("attributes", {})
        container.current_status = attributes.get("status")
        container.location = attributes.get("location")
        
        db.commit()
        
        logger.info(f"Processed webhook for container {container.container_number}: {event_type}")
        
        return {"status": "processed", "container": container.container_number}
        
    except Exception as e:
        logger.error(f"Error processing Terminal49 webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

