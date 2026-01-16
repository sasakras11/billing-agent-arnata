"""Billing charge models."""
from datetime import datetime, date
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship

from models.database import Base


class ChargeType(str, Enum):
    """Types of charges that can be billed."""
    BASE_FREIGHT = "base_freight"
    PER_DIEM = "per_diem"



class Charge(Base):
    """Individual charge line item for billing."""
    
    __tablename__ = "charges"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # References
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    container_id = Column(Integer, ForeignKey("containers.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    
    # Charge Details
    charge_type = Column(SQLEnum(ChargeType), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    
    # Calculation
    rate = Column(Float, nullable=False)  # Rate per unit (day, lb, etc.)
    quantity = Column(Float, default=1.0)  # Number of days, weight, etc.
    amount = Column(Float, nullable=False)  # Total charge amount
    
    # Time Period
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Billing Status
    is_billable = Column(Boolean, default=True)  # Can be billed to customer
    is_approved = Column(Boolean, default=False)  # Approved by human
    is_disputed = Column(Boolean, default=False)
    
    # Customer vs Company
    billable_to_customer = Column(Boolean, default=True)
    absorbed_by_company = Column(Boolean, default=False)
    
    # Supporting Documentation
    documentation_url = Column(String(500))  # Link to BOL, gate ticket, etc.
    notes = Column(Text)
    
    # AI Analysis
    ai_confidence_score = Column(Float)  # 0-1 confidence in charge calculation
    ai_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime)
    
    # Relationships
    load = relationship("Load", back_populates="charges")
    container = relationship("Container", back_populates="charges")
    invoice = relationship("Invoice", back_populates="charges")
    
    def __repr__(self):
        return f"<Charge(type='{self.charge_type}', amount=${self.amount})>"

