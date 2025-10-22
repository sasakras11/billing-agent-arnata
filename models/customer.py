"""Customer model."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from models.database import Base


class Customer(Base):
    """Customer with billing rate contracts."""
    
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Info
    mcleod_customer_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    
    # QuickBooks Integration
    quickbooks_customer_id = Column(String(50), unique=True, index=True)
    
    # Billing Rates (per day)
    per_diem_rate = Column(Float, default=100.0)
    demurrage_rate = Column(Float, default=150.0)
    detention_rate = Column(Float, default=125.0)
    chassis_split_fee = Column(Float, default=50.0)
    pre_pull_fee = Column(Float, default=75.0)
    
    # Free Time Configuration
    free_days = Column(Integer, default=3)
    per_diem_free_days = Column(Integer, default=3)
    demurrage_free_days = Column(Integer, default=2)
    
    # Settings
    auto_invoice = Column(Boolean, default=True)
    send_alerts = Column(Boolean, default=True)
    alert_email = Column(String(255))
    alert_phone = Column(String(50))
    
    # Contract Details
    contract_notes = Column(Text)
    payment_terms = Column(String(50), default="Net 30")
    
    # Status
    active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    loads = relationship("Load", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.id}, name='{self.name}')>"

