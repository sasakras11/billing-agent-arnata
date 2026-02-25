"""Alert and notification service."""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client as TwilioClient

from models import Alert, AlertType, AlertStatus, Container, Invoice, Customer
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AlertService:
    """Manage alerts and notifications."""
    
    def __init__(self, db: Session):
        """
        Initialize alert service.
        
        Args:
            db: Database session
        """
        self.db = db
        
        # Initialize email client
        if settings.sendgrid_api_key:
            self.sendgrid_client = SendGridAPIClient(settings.sendgrid_api_key)
        else:
            self.sendgrid_client = None
            logger.warning("SendGrid API key not configured")
        
        # Initialize SMS client
        if settings.twilio_account_sid and settings.twilio_auth_token:
            self.twilio_client = TwilioClient(
                settings.twilio_account_sid,
                settings.twilio_auth_token
            )
        else:
            self.twilio_client = None
            logger.warning("Twilio credentials not configured")
    
    def _save_alert(self, alert: Alert, log_message: str) -> Optional[Alert]:
        """Persist an alert and log; rollback and return None on error."""
        try:
            self.db.add(alert)
            self.db.commit()
            logger.info(log_message)
            return alert
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            self.db.rollback()
            return None

    def create_per_diem_alert(
        self, container: Container, customer: Customer, hours_until: int
    ) -> Optional[Alert]:
        """Create per diem warning alert."""
        existing = (
            self.db.query(Alert)
            .filter(
                Alert.container_id == container.id,
                Alert.alert_type == AlertType.PER_DIEM_WARNING,
                Alert.status.in_([AlertStatus.PENDING, AlertStatus.SENT]),
            )
            .first()
        )
        if existing:
            logger.info(f"Per diem alert already exists for container {container.container_number}")
            return existing

        priority = "urgent" if hours_until <= 6 else "high" if hours_until <= 24 else "medium"
        alert = Alert(
            alert_type=AlertType.PER_DIEM_WARNING,
            priority=priority,
            customer_id=customer.id,
            container_id=container.id,
            load_id=container.load.id if container.load else None,
            recipient_email=customer.alert_email or customer.email,
            recipient_phone=customer.alert_phone or customer.phone,
            subject=f"⚠️ Per Diem Alert: Container {container.container_number}",
            message=self._format_per_diem_message(container, hours_until),
            send_email=customer.send_alerts and bool(customer.alert_email or customer.email),
            send_sms=priority == "urgent" and bool(customer.alert_phone or customer.phone),
            scheduled_for=datetime.utcnow(),
            metadata={
                "container_number": container.container_number,
                "hours_until": hours_until,
                "per_diem_starts": container.per_diem_starts.isoformat() if container.per_diem_starts else None,
            },
        )
        return self._save_alert(
            alert,
            f"Created per diem alert for container {container.container_number}, priority: {priority}",
        )

    def create_container_available_alert(
        self, container: Container, customer: Customer
    ) -> Optional[Alert]:
        """Create alert when container is available for pickup."""
        alert = Alert(
            alert_type=AlertType.CONTAINER_AVAILABLE,
            priority="high",
            customer_id=customer.id,
            container_id=container.id,
            load_id=container.load.id if container.load else None,
            recipient_email=customer.alert_email or customer.email,
            recipient_phone=customer.alert_phone or customer.phone,
            subject=f"📦 Container Available: {container.container_number}",
            message=self._format_available_message(container),
            send_email=True,
            scheduled_for=datetime.utcnow(),
            metadata={
                "container_number": container.container_number,
                "location": container.location,
                "last_free_day": container.last_free_day.isoformat() if container.last_free_day else None,
            },
        )
        return self._save_alert(alert, f"Created availability alert for container {container.container_number}")

    def create_charge_accruing_alert(
        self, container: Container, customer: Customer, charge_type: str, daily_rate: float
    ) -> Optional[Alert]:
        """Create alert when charges are actively accruing."""
        alert = Alert(
            alert_type=AlertType.CHARGE_ACCRUING,
            priority="urgent",
            customer_id=customer.id,
            container_id=container.id,
            load_id=container.load.id if container.load else None,
            recipient_email=customer.alert_email or customer.email,
            recipient_phone=customer.alert_phone or customer.phone,
            subject=f"🚨 Charges Accruing: Container {container.container_number}",
            message=self._format_accruing_message(container, charge_type, daily_rate),
            send_email=True,
            send_sms=True,
            scheduled_for=datetime.utcnow(),
            metadata={"container_number": container.container_number, "charge_type": charge_type, "daily_rate": daily_rate},
        )
        return self._save_alert(alert, f"Created charge accruing alert for container {container.container_number}")

    def create_invoice_alert(self, invoice: Invoice, customer: Customer) -> Optional[Alert]:
        """Create alert when invoice is created."""
        alert = Alert(
            alert_type=AlertType.INVOICE_CREATED,
            priority="medium",
            customer_id=customer.id,
            invoice_id=invoice.id,
            recipient_email=customer.alert_email or customer.email,
            subject=f"💰 Invoice Created: {invoice.invoice_number}",
            message=self._format_invoice_message(invoice),
            send_email=True,
            scheduled_for=datetime.utcnow(),
            metadata={
                "invoice_number": invoice.invoice_number,
                "total_amount": float(invoice.total_amount),
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            },
        )
        return self._save_alert(alert, f"Created invoice alert for {invoice.invoice_number}")
    
    def send_pending_alerts(self, limit: int = 50) -> int:
        """
        Send all pending alerts.
        
        Args:
            limit: Maximum number of alerts to send
            
        Returns:
            Number of alerts sent
        """
        try:
            # Get pending alerts
            now = datetime.utcnow()
            alerts = (
                self.db.query(Alert)
                .filter(
                    Alert.status == AlertStatus.PENDING,
                    Alert.scheduled_for <= now,
                    Alert.retry_count < Alert.max_retries
                )
                .limit(limit)
                .all()
            )
            
            sent_count = 0
            for alert in alerts:
                if self.send_alert(alert):
                    sent_count += 1
            
            logger.info(f"Sent {sent_count} of {len(alerts)} pending alerts")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending pending alerts: {e}")
            return 0
    
    def send_alert(self, alert: Alert) -> bool:
        """
        Send individual alert.
        
        Args:
            alert: Alert object
            
        Returns:
            True if successful
        """
        try:
            success = False
            
            # Send email
            if alert.send_email and alert.recipient_email:
                if self._send_email(
                    to_email=alert.recipient_email,
                    subject=alert.subject,
                    message=alert.message
                ):
                    alert.email_sent = True
                    success = True
            
            # Send SMS
            if alert.send_sms and alert.recipient_phone:
                if self._send_sms(
                    to_phone=alert.recipient_phone,
                    message=alert.subject  # Send short subject for SMS
                ):
                    alert.sms_sent = True
                    success = True
            
            # Update alert status
            if success:
                alert.status = AlertStatus.SENT
                alert.sent_at = datetime.utcnow()
            else:
                alert.retry_count += 1
                if alert.retry_count >= alert.max_retries:
                    alert.status = AlertStatus.FAILED
            
            self.db.commit()
            return success
            
        except Exception as e:
            logger.error(f"Error sending alert {alert.id}: {e}")
            alert.retry_count += 1
            alert.last_error = str(e)
            self.db.commit()
            return False
    
    def _send_email(self, to_email: str, subject: str, message: str) -> bool:
        """Send email via SendGrid."""
        try:
            if not self.sendgrid_client:
                logger.warning("Email not sent - SendGrid not configured")
                return False
            
            email = Mail(
                from_email="alerts@billing-agent.com",  # Configure your sender
                to_emails=to_email,
                subject=subject,
                html_content=message
            )
            
            response = self.sendgrid_client.send(email)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent to {to_email}")
                return True
            else:
                logger.error(f"Email failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def _send_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS via Twilio."""
        try:
            if not self.twilio_client:
                logger.warning("SMS not sent - Twilio not configured")
                return False
            
            sms = self.twilio_client.messages.create(
                body=message[:160],  # SMS character limit
                from_=settings.twilio_phone_number,
                to=to_phone
            )
            
            logger.info(f"SMS sent to {to_phone}: {sms.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False
    
    def _format_per_diem_message(self, container: Container, hours_until: int) -> str:
        """Format per diem alert message."""
        return f"""
        <h2>Per Diem Charges Starting Soon</h2>
        <p>Container <strong>{container.container_number}</strong> will start accruing per diem charges in <strong>{hours_until} hours</strong>.</p>
        <p><strong>Per Diem Starts:</strong> {container.per_diem_starts.strftime('%Y-%m-%d %H:%M') if container.per_diem_starts else 'Unknown'}</p>
        <p><strong>Current Location:</strong> {container.location or 'Unknown'}</p>
        <p><strong>Action Required:</strong> Return container before per diem charges start to avoid additional fees.</p>
        """
    
    def _format_available_message(self, container: Container) -> str:
        """Format container available message."""
        return f"""
        <h2>Container Available for Pickup</h2>
        <p>Container <strong>{container.container_number}</strong> is now available for pickup.</p>
        <p><strong>Location:</strong> {container.location or 'Unknown'}</p>
        <p><strong>Last Free Day:</strong> {container.last_free_day.strftime('%Y-%m-%d') if container.last_free_day else 'Unknown'}</p>
        <p><strong>Action Required:</strong> Schedule pickup as soon as possible to maximize free time.</p>
        """
    
    def _format_accruing_message(self, container: Container, charge_type: str, daily_rate: float) -> str:
        """Format charge accruing message."""
        return f"""
        <h2>⚠️ Charges Currently Accruing</h2>
        <p>Container <strong>{container.container_number}</strong> is currently accruing <strong>{charge_type}</strong> charges.</p>
        <p><strong>Daily Rate:</strong> ${daily_rate:.2f}/day</p>
        <p><strong>Current Location:</strong> {container.location or 'Unknown'}</p>
        <p><strong>Urgent Action Required:</strong> Immediate attention needed to minimize additional charges.</p>
        """
    
    def _format_invoice_message(self, invoice: Invoice) -> str:
        """Format invoice created message."""
        return f"""
        <h2>New Invoice Created</h2>
        <p>Invoice <strong>{invoice.invoice_number}</strong> has been created.</p>
        <p><strong>Total Amount:</strong> ${invoice.total_amount:.2f}</p>
        <p><strong>Due Date:</strong> {invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'Upon Receipt'}</p>
        <p>The invoice will be sent to you shortly via QuickBooks.</p>
        """

