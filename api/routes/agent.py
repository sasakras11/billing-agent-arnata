"""AI Agent endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models import get_db
from repositories.container_repository import ContainerRepository
from repositories.invoice_repository import InvoiceRepository
from agents import TrackingAgent, BillingAgent, DisputeAgent

router = APIRouter()


class QueryRequest(BaseModel):
    query: str


class AnalyzeRequest(BaseModel):
    container_number: str


class DisputeRequest(BaseModel):
    invoice_id: int
    reason: str | None = None


def _find_container_in_query(query_text: str, db: Session):
    """Extract container number from query (11 alphanumeric chars) and fetch from DB."""
    repo = ContainerRepository(db)
    for word in query_text.split():
        if len(word) == 11 and word.isalnum():
            return repo.get_by_container_number(word.upper())
    return None


@router.post("/query")
async def agent_query(request: QueryRequest, db: Session = Depends(get_db)):
    """Natural language query to AI agent."""
    query = request.query.lower()
    if "status" in query and "container" in query:
        container = _find_container_in_query(request.query, db)
        if container:
            return {
                "response": f"Container {container.container_number} is currently {container.current_status} at {container.location or 'unknown location'}.",
                "container": {"number": container.container_number, "status": container.current_status, "location": container.location},
            }
    return {"response": "I understand your query. For detailed information, please use specific endpoints or provide more details."}


@router.post("/analyze")
async def analyze_container(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """Analyze container for charge risk."""
    container = ContainerRepository(db).get_by_container_number(request.container_number)
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    return await TrackingAgent(db).analyze_container_risk(container)


@router.post("/draft-dispute-response")
async def draft_dispute_response(request: DisputeRequest, db: Session = Depends(get_db)):
    """Draft response to invoice dispute."""
    invoice = InvoiceRepository(db).get_by_id(request.invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return await DisputeAgent(db).draft_dispute_response(invoice, request.reason)
