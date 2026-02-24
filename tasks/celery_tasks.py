"""Celery background tasks."""
import logging
from datetime import datetime, date

from tasks.celery_app import celery_app
from models.database import db_session
from models import Load, Container, Invoice, InvoiceStatus, Customer, Alert, AlertStatus
from integrations.mcleod_client import McLeodClient
from agents.tracking_agent import TrackingAgent
from agents.billing_agent import BillingAgent
from services.alert_service import AlertService
from services.invoice_generator import InvoiceGenerator

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.celery_tasks.sync_mcleod_loads")
def sync_mcleod_loads():
    """Sync new loads from McLeod LoadMaster."""
    with db_session() as db:
        try:
            logger.info("Starting McLeod load sync")
            mcleod = McLeodClient()
            loads = mcleod.get_recent_loads(minutes=15)
            new_loads = 0
            tracked_containers = 0

            for mcleod_load in loads:
                existing = db.query(Load).filter(Load.mcleod_order_id == mcleod_load.order_id).first()
                if existing:
                    continue

                customer = db.query(Customer).filter(Customer.mcleod_customer_id == mcleod_load.customer_id).first()
                if not customer:
                    customer = Customer(mcleod_customer_id=mcleod_load.customer_id, name=mcleod_load.customer_name)
                    db.add(customer)
                    db.flush()

                load = Load(
                    mcleod_order_id=mcleod_load.order_id,
                    mcleod_load_number=mcleod_load.load_number,
                    customer_id=customer.id,
                    container_number=mcleod_load.container_number,
                    booking_number=mcleod_load.booking_number,
                    bill_of_lading=mcleod_load.bill_of_lading,
                    shipper_name=mcleod_load.shipper_name,
                    consignee_name=mcleod_load.consignee_name,
                    pickup_location=mcleod_load.pickup_location,
                    pickup_terminal=mcleod_load.pickup_terminal,
                    delivery_location=mcleod_load.delivery_location,
                    pickup_date=mcleod_load.pickup_date.date() if mcleod_load.pickup_date else None,
                    scheduled_delivery_date=mcleod_load.scheduled_delivery_date.date() if mcleod_load.scheduled_delivery_date else None,
                    actual_delivery_date=mcleod_load.actual_delivery_date.date() if mcleod_load.actual_delivery_date else None,
                    base_freight_rate=mcleod_load.base_freight_rate,
                    equipment_type=mcleod_load.equipment_type,
                    cargo_weight=mcleod_load.cargo_weight,
                    status=mcleod_load.status,
                    last_synced_at=datetime.utcnow(),
                )
                db.add(load)
                db.commit()
                new_loads += 1

                if load.container_number:
                    container = TrackingAgent(db).start_tracking_container(load.container_number, load)
                    if container:
                        tracked_containers += 1

            logger.info(f"McLeod sync complete: {new_loads} new loads, {tracked_containers} containers tracked")
            return {"new_loads": new_loads, "tracked_containers": tracked_containers}

        except Exception as e:
            logger.error(f"Error syncing McLeod loads: {e}")
            raise


@celery_app.task(name="tasks.celery_tasks.update_container_statuses")
def update_container_statuses():
    """Update container statuses from Terminal49."""
    with db_session() as db:
        try:
            logger.info("Starting container status updates")
            containers = (
                db.query(Container)
                .filter(Container.is_tracking_active == True, Container.returned_empty.is_(None))
                .all()
            )
            tracking_agent = TrackingAgent(db)
            updated = 0
            for container in containers:
                try:
                    if tracking_agent.update_container_status(container):
                        updated += 1
                except Exception as e:
                    logger.error(f"Error updating container {container.id}: {e}")

            logger.info(f"Container status update complete: {updated} containers updated")
            return {"updated": updated, "total": len(containers)}

        except Exception as e:
            logger.error(f"Error updating container statuses: {e}")
            raise


@celery_app.task(name="tasks.celery_tasks.check_and_send_alerts")
def check_and_send_alerts():
    """Check containers and send alerts."""
    with db_session() as db:
        try:
            logger.info("Checking for alerts")
            containers = (
                db.query(Container)
                .filter(Container.is_tracking_active == True, Container.returned_empty.is_(None))
                .all()
            )
            tracking_agent = TrackingAgent(db)
            alert_service = AlertService(db)
            alerts_created = 0
            for container in containers:
                try:
                    alerts_created += len(tracking_agent.check_alerts(container))
                except Exception as e:
                    logger.error(f"Error checking alerts for container {container.id}: {e}")

            alerts_sent = alert_service.send_pending_alerts()
            logger.info(f"Alert check complete: {alerts_created} alerts created, {alerts_sent} alerts sent")
            return {"alerts_created": alerts_created, "alerts_sent": alerts_sent}

        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            raise


@celery_app.task(name="tasks.celery_tasks.process_pending_invoices")
def process_pending_invoices():
    """Process loads ready for billing."""
    with db_session() as db:
        try:
            logger.info("Processing pending invoices")
            loads = (
                db.query(Load)
                .filter(Load.status == "delivered", Load.actual_delivery_date.isnot(None))
                .all()
            )
            billing_agent = BillingAgent(db)
            invoices_created = 0
            for load in loads:
                if load.charges and any(c.invoice_id is not None for c in load.charges):
                    continue
                try:
                    invoice = billing_agent.process_load_billing(load, auto_approve=False)
                    if invoice:
                        invoices_created += 1
                except Exception as e:
                    logger.error(f"Error processing billing for load {load.id}: {e}")

            logger.info(f"Invoice processing complete: {invoices_created} invoices created")
            return {"invoices_created": invoices_created, "loads_processed": len(loads)}

        except Exception as e:
            logger.error(f"Error processing invoices: {e}")
            raise


@celery_app.task(name="tasks.celery_tasks.check_payment_status")
def check_payment_status():
    """Check payment status for open invoices."""
    with db_session() as db:
        try:
            logger.info("Checking payment status")
            invoices = (
                db.query(Invoice)
                .filter(
                    Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]),
                    Invoice.quickbooks_invoice_id.isnot(None),
                )
                .all()
            )
            invoice_generator = InvoiceGenerator(db)
            updated = 0
            for invoice in invoices:
                try:
                    if invoice_generator.check_payment_status(invoice):
                        updated += 1
                except Exception as e:
                    logger.error(f"Error checking payment for invoice {invoice.id}: {e}")

            logger.info(f"Payment status check complete: {updated} invoices updated")
            return {"updated": updated, "total": len(invoices)}

        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            raise


@celery_app.task(name="tasks.celery_tasks.generate_daily_report")
def generate_daily_report():
    """Generate daily summary report."""
    with db_session() as db:
        try:
            logger.info("Generating daily report")
            today = date.today()
            active_filter = [Container.is_tracking_active == True, Container.returned_empty.is_(None)]
            active_containers = db.query(Container).filter(*active_filter).count()
            at_risk = db.query(Container).filter(*active_filter, Container.last_free_day <= today).count()
            pending_alerts = db.query(Alert).filter(Alert.status == AlertStatus.PENDING).count()
            metrics = BillingAgent(db).get_billing_metrics(days=1)

            report = {
                "date": today.isoformat(),
                "active_containers": active_containers,
                "containers_at_risk": at_risk,
                "pending_alerts": pending_alerts,
                **metrics,
            }
            logger.info(f"Daily report generated: {report}")
            return report

        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            raise
