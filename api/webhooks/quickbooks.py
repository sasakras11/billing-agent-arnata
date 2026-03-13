"""QuickBooks webhook handler."""
import logging
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session

from models import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/quickbooks")
async def handle_quickbooks_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle QuickBooks payment notifications."""
    try:
        payload = await request.json()
        event_notifications = payload.get("eventNotifications", [])

        for notification in event_notifications:
            for entity in notification.get("dataChangeEvent", {}).get("entities", []):
                entity_name = entity.get("name")
                entity_id = entity.get("id")
                operation = entity.get("operation")

                if entity_name == "Payment" and operation in ["Create", "Update"]:
                    logger.info(f"Payment notification received: {entity_id}")
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"Error processing QuickBooks webhook: {e}")
        return {"status": "error", "detail": str(e)}

