"""Alert and notification models."""
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean, JSON
from sqlalchemy.orm import relationship

from models.database import Base


class AlertType(str, Enum):
    """Types of alerts."""
    PER_DIEM_WARNING = "per_diem_warning"
    DEMURRAGE_WARNING = "demurrage_warning"
    DETENTION_WARNING = "detention_warning"
    CHARGE_ACCRUING = "charge_accruing"
    CONTAINER_AVAILABLE = "container_available"
    CONTAINER_AT_RISK = "container_at_risk"
    INVOICE_CREATED = "invoice_created"
    PAYMENT_RECEIVED = "payment_received"
    DISPUTE_DETECTED = "dispute_detected"
    TRACKING_ISSUE = "tracking_issue"
    GENERAL = "general"


class AlertStatus(str, Enum):
    """Alert status."""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    FAILED = "failed"


class Alert(Base):
    """Alert/notification to be sent to users."""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(SQLEnum(AlertType), nullable=False, index=True)
    priority = Column(String(20), default="medium")
    customer_id = Column(Integer, ForeignKey("customers.id"))
    recipient_email = Column(String(255))
    recipient_phone = Column(String(50))
    container_id = Column(Integer, ForeignKey("containers.id"))
    load_id = Column(Integer, ForeignKey("loads.id"))
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    send_email = Column(Boolean, default=True)
    send_sms = Column(Boolean, default=False)
    send_webhook = Column(Boolean, default=False)
    webhook_url = Column(String(500))
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.PENDING, index=True)
    scheduled_for = Column(DateTime)
    sent_at = Column(DateTime)
    acknowledged_at = Column(DateTime)
    email_sent = Column(Boolean, default=False)
    sms_sent = Column(Boolean, default=False)
    webhook_sent = Column(Boolean, default=False)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_error = Column(Text)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    customer = relationship("Customer")
    container = relationship("Container", back_populates="alerts")
    load = relationship("Load")
    invoice = relationship("Invoice")
    
    def __repr__(self):
        return f"<Alert(type='{self.alert_type}', priority='{self.priority}', status='{self.status}')>"

