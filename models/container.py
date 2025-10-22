"""Container tracking models."""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship

from models.database import Base


class Container(Base):
    """Container tracked via Terminal49."""
    
    __tablename__ = "containers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Container Info
    container_number = Column(String(50), unique=True, nullable=False, index=True)
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    
    # Terminal49 Data
    terminal49_tracking_id = Column(String(100), unique=True, index=True)
    shipping_line = Column(String(100))
    
    # Vessel Information
    vessel_name = Column(String(255))
    voyage_number = Column(String(100))
    
    # Locations
    pol_name = Column(String(255))  # Port of Loading
    pod_name = Column(String(255))  # Port of Discharge
    destination_terminal = Column(String(255))
    
    # Key Milestones
    vessel_departed_pol = Column(DateTime)
    vessel_arrived_pod = Column(DateTime)
    vessel_discharged = Column(DateTime)
    rail_loaded = Column(DateTime)
    rail_departed = Column(DateTime)
    rail_arrived = Column(DateTime)
    available_for_pickup = Column(DateTime)
    picked_up = Column(DateTime)
    delivered = Column(DateTime)
    returned_empty = Column(DateTime)
    
    # Free Time Calculation
    last_free_day = Column(Date)
    per_diem_starts = Column(Date)
    demurrage_starts = Column(Date)
    detention_starts = Column(Date)
    
    # Charge Tracking
    per_diem_days = Column(Integer, default=0)
    demurrage_days = Column(Integer, default=0)
    detention_days = Column(Integer, default=0)
    
    # Status
    current_status = Column(String(100))
    location = Column(String(255))
    holds = Column(JSON)  # Any customs or freight holds
    
    # Tracking Status
    is_tracking_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Raw Data
    raw_terminal49_data = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    load = relationship("Load", back_populates="container")
    events = relationship("ContainerEvent", back_populates="container", order_by="ContainerEvent.event_time")
    charges = relationship("Charge", back_populates="container")
    alerts = relationship("Alert", back_populates="container")
    
    def __repr__(self):
        return f"<Container(number='{self.container_number}', status='{self.current_status}')>"


class ContainerEvent(Base):
    """Individual container milestone events from Terminal49."""
    
    __tablename__ = "container_events"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Container Reference
    container_id = Column(Integer, ForeignKey("containers.id"), nullable=False)
    
    # Event Details
    event_type = Column(String(100), nullable=False, index=True)
    event_time = Column(DateTime, nullable=False)
    location = Column(String(255))
    vessel = Column(String(255))
    voyage = Column(String(100))
    
    # Event Data
    description = Column(Text)
    raw_data = Column(JSON)
    
    # Tracking
    terminal49_event_id = Column(String(100), unique=True)
    received_at = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    container = relationship("Container", back_populates="events")
    
    def __repr__(self):
        return f"<ContainerEvent(type='{self.event_type}', time='{self.event_time}')>"

