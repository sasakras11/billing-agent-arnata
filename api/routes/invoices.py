"""Invoice endpoints."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from models import get_db, Invoice

router = APIRouter()


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    total_amount: float
    status: str


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all invoices."""
    invoices = db.query(Invoice).offset(skip).limit(limit).all()
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/invoices/{invoice_id}/send")
async def send_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Send invoice to customer."""
    from services import InvoiceGenerator
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    generator = InvoiceGenerator(db)
    success = generator.send_to_customer(invoice)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send invoice")
    
    return {"status": "sent", "invoice_number": invoice.invoice_number}

