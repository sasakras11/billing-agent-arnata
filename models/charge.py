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
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    container_id = Column(Integer, ForeignKey("containers.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    charge_type = Column(SQLEnum(ChargeType), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    rate = Column(Float, nullable=False)
    quantity = Column(Float, default=1.0)
    amount = Column(Float, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    is_billable = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=False)
    is_disputed = Column(Boolean, default=False)
    billable_to_customer = Column(Boolean, default=True)
    absorbed_by_company = Column(Boolean, default=False)
    documentation_url = Column(String(500))
    notes = Column(Text)
    ai_confidence_score = Column(Float)
    ai_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_at = Column(DateTime)
    load = relationship("Load", back_populates="charges")
    container = relationship("Container", back_populates="charges")
    invoice = relationship("Invoice", back_populates="charges")
    
    def __repr__(self):
        return f"<Charge(type='{self.charge_type}', amount=${self.amount})>"

