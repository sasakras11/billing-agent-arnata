"""AI Agent endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import get_db, Container, Customer
from agents import TrackingAgent, BillingAgent, DisputeAgent

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


class AnalyzeRequest(BaseModel):
    container_number: str


class DisputeRequest(BaseModel):
    invoice_id: int
    reason: str | None = None


@router.post("/query")
async def agent_query(request: QueryRequest, db: Session = Depends(get_db)):
    """Natural language query to AI agent."""
    # Simple implementation - can be enhanced with full NL processing
    query = request.query.lower()
    
    if "status" in query and "container" in query:
        # Extract container number (simplified)
        words = request.query.split()
        for word in words:
            if len(word) == 11 and word.isalnum():  # Container number pattern
                container = (
                    db.query(Container)
                    .filter(Container.container_number == word.upper())
                    .first()
                )
                if container:
                    return {
                        "response": f"Container {container.container_number} is currently {container.current_status} at {container.location or 'unknown location'}.",
                        "container": {
                            "number": container.container_number,
                            "status": container.current_status,
                            "location": container.location,
                        }
                    }
    
    return {
        "response": "I understand your query. For detailed information, please use specific endpoints or provide more details."
    }


@router.post("/analyze")
async def analyze_container(
    request: AnalyzeRequest,
    db: Session = Depends(get_db)
):
    """Analyze container for charge risk."""
    container = (
        db.query(Container)
        .filter(Container.container_number == request.container_number)
        .first()
    )
    
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    agent = TrackingAgent(db)
    analysis = await agent.analyze_container_risk(container)
    
    return analysis


@router.post("/draft-dispute-response")
async def draft_dispute_response(
    request: DisputeRequest,
    db: Session = Depends(get_db)
):
    """Draft response to invoice dispute."""
    from models import Invoice
    
    invoice = db.query(Invoice).filter(Invoice.id == request.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    agent = DisputeAgent(db)
    draft = await agent.draft_dispute_response(invoice, request.reason)
    
    return draft

