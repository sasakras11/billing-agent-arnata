"""Invoice models."""
from datetime import datetime, date
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship

from models.database import Base


class InvoiceStatus(str, Enum):
    """Invoice status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"


class Invoice(Base):
    """Invoice in QuickBooks."""
    
    __tablename__ = "invoices"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Invoice Details
    invoice_number = Column(String(50), unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # QuickBooks Integration
    quickbooks_invoice_id = Column(String(50), unique=True, index=True)
    quickbooks_sync_token = Column(String(50))  # For updates
    
    # Amounts
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    balance_due = Column(Float)
    
    # Dates
    invoice_date = Column(Date, nullable=False, default=date.today)
    due_date = Column(Date)
    sent_date = Column(Date)
    paid_date = Column(Date)
    
    # Status
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.DRAFT, index=True)
    
    # Payment Details
    payment_terms = Column(String(50), default="Net 30")
    payment_method = Column(String(50))
    
    # Dispute Handling
    is_disputed = Column(Boolean, default=False)
    dispute_amount = Column(Float)
    dispute_reason = Column(Text)
    dispute_resolved = Column(Boolean, default=False)
    
    # AI Generated
    ai_generated = Column(Boolean, default=True)
    requires_human_review = Column(Boolean, default=False)
    
    # Supporting Documents
    attachment_urls = Column(Text)  # JSON array of document URLs
    
    # Notes
    memo = Column(Text)
    internal_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime)
    
    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    charges = relationship("Charge", back_populates="invoice")
    line_items = relationship("InvoiceLineItem", back_populates="invoice")
    
    def __repr__(self):
        return f"<Invoice(number='{self.invoice_number}', total=${self.total_amount}, status='{self.status}')>"


class InvoiceLineItem(Base):
    """Individual line item on an invoice."""
    
    __tablename__ = "invoice_line_items"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Invoice Reference
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    
    # Line Item Details
    item_number = Column(Integer)  # Line number on invoice
    description = Column(String(500), nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    
    # QuickBooks Integration
    quickbooks_item_id = Column(String(50))  # Reference to QB item/service
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="line_items")
    
    def __repr__(self):
        return f"<InvoiceLineItem(description='{self.description}', amount=${self.amount})>"

