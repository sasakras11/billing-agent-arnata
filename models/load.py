"""Load model from McLeod LoadMaster."""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from models.database import Base


class Load(Base):
    """Drayage load from McLeod LoadMaster TMS."""
    
    __tablename__ = "loads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # McLeod Data
    mcleod_order_id = Column(String(50), unique=True, nullable=False, index=True)
    mcleod_load_number = Column(String(50), unique=True, index=True)
    
    # Customer
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    
    # Container Information
    container_number = Column(String(50), index=True)
    booking_number = Column(String(50))
    bill_of_lading = Column(String(50))
    
    # Shipment Details
    shipper_name = Column(String(255))
    consignee_name = Column(String(255))
    
    # Locations
    pickup_location = Column(String(255))
    pickup_terminal = Column(String(255))
    delivery_location = Column(String(255))
    
    # Dates
    pickup_date = Column(Date)
    scheduled_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    
    # Freight Details
    base_freight_rate = Column(Float)
    equipment_type = Column(String(50))  # 20GP, 40HC, etc.
    cargo_weight = Column(Float)
    
    # Status
    status = Column(String(50), default="pending")  # pending, in_transit, delivered, billed
    
    # Tracking
    is_tracking_active = Column(Boolean, default=False)
    last_synced_at = Column(DateTime)
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="loads")
    container = relationship("Container", back_populates="load", uselist=False)
    charges = relationship("Charge", back_populates="load")
    
    def __repr__(self):
        return f"<Load(id={self.id}, order='{self.mcleod_order_id}', container='{self.container_number}')>"

