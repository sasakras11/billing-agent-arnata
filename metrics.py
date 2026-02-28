"""Metrics and reporting utilities for system monitoring."""
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models import (
    Invoice,
    InvoiceStatus,
    Load,
    Container,
    Charge,
    ChargeType,
    Customer,
)
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BillingMetrics:
    """Container for billing metrics."""
    
    total_revenue: float
    total_invoices: int
    paid_invoices: int
    outstanding_invoices: int
    disputed_invoices: int
    average_invoice_amount: float
    total_charges: int
    total_per_diem_charges: float
    total_demurrage_charges: float
    total_detention_charges: float
    period_start: date
    period_end: date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ContainerMetrics:
    """Container for container tracking metrics."""
    
    total_containers: int
    active_containers: int
    returned_containers: int
    containers_with_charges: int
    average_dwell_time_days: float
    on_time_return_rate: float
    period_start: date
    period_end: date
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CustomerMetrics:
    """Container for customer-specific metrics."""
    
    customer_name: str
    total_loads: int
    total_invoiced: float
    total_paid: float
    outstanding_balance: float
    average_payment_days: float
    dispute_rate: float
    on_time_payment_rate: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class MetricsCollector:
    """Collect and calculate system metrics."""
    
    def __init__(self, db: Session):
        """
        Initialize metrics collector.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_billing_metrics(
        self,
        start_date: date,
        end_date: date
    ) -> BillingMetrics:
        """
        Get billing metrics for date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            BillingMetrics
        """
        logger.info(f"Calculating billing metrics for {start_date} to {end_date}")
        
        # Get invoices in date range
        invoices = self.db.query(Invoice).filter(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date
            )
        ).all()
        
        # Calculate totals
        total_revenue = sum(inv.total_amount for inv in invoices)
        total_invoices = len(invoices)
        
        paid_invoices = sum(
            1 for inv in invoices if inv.status == InvoiceStatus.PAID
        )
        
        outstanding_invoices = sum(
            1 for inv in invoices
            if inv.status in [
                InvoiceStatus.SENT,
                InvoiceStatus.PENDING_APPROVAL,
                InvoiceStatus.OVERDUE,
            ]
        )
        
        disputed_invoices = sum(
            1 for inv in invoices if inv.status == InvoiceStatus.DISPUTED
        )
        
        average_invoice_amount = (
            total_revenue / total_invoices if total_invoices > 0 else 0.0
        )
        
        # Get charge breakdown
        charges = self.db.query(Charge).join(Invoice).filter(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date
            )
        ).all()
        
        total_charges = len(charges)
        
        total_per_diem = sum(
            c.amount for c in charges if c.charge_type == ChargeType.PER_DIEM
        )
        
        total_demurrage = sum(
            c.amount for c in charges if c.charge_type == ChargeType.DEMURRAGE
        )
        
        total_detention = sum(
            c.amount for c in charges if c.charge_type == ChargeType.DETENTION
        )
        
        return BillingMetrics(
            total_revenue=float(total_revenue),
            total_invoices=total_invoices,
            paid_invoices=paid_invoices,
            outstanding_invoices=outstanding_invoices,
            disputed_invoices=disputed_invoices,
            average_invoice_amount=float(average_invoice_amount),
            total_charges=total_charges,
            total_per_diem_charges=float(total_per_diem),
            total_demurrage_charges=float(total_demurrage),
            total_detention_charges=float(total_detention),
            period_start=start_date,
            period_end=end_date,
        )
    
    def get_container_metrics(
        self,
        start_date: date,
        end_date: date
    ) -> ContainerMetrics:
        """
        Get container tracking metrics for date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            ContainerMetrics
        """
        logger.info(f"Calculating container metrics for {start_date} to {end_date}")
        
        # Get containers in date range
        containers = self.db.query(Container).filter(
            and_(
                Container.vessel_discharged >= datetime.combine(start_date, datetime.min.time()),
                Container.vessel_discharged <= datetime.combine(end_date, datetime.max.time())
            )
        ).all()
        
        total_containers = len(containers)
        
        active_containers = sum(
            1 for c in containers if c.returned_empty is None
        )
        
        returned_containers = sum(
            1 for c in containers if c.returned_empty is not None
        )
        
        containers_with_charges = sum(
            1 for c in containers
            if c.per_diem_starts and (
                c.returned_empty is None or
                c.returned_empty.date() > c.per_diem_starts
            )
        )
        
        # Calculate average dwell time (discharge to return)
        dwell_times = []
        for c in containers:
            if c.vessel_discharged and c.returned_empty:
                dwell = (c.returned_empty - c.vessel_discharged).days
                dwell_times.append(dwell)
        
        average_dwell = (
            sum(dwell_times) / len(dwell_times) if dwell_times else 0.0
        )
        
        # Calculate on-time return rate
        on_time_returns = sum(
            1 for c in containers
            if c.returned_empty and c.per_diem_starts
            and c.returned_empty.date() <= c.per_diem_starts
        )
        
        returnable = sum(
            1 for c in containers if c.per_diem_starts
        )
        
        on_time_rate = (
            (on_time_returns / returnable * 100) if returnable > 0 else 0.0
        )
        
        return ContainerMetrics(
            total_containers=total_containers,
            active_containers=active_containers,
            returned_containers=returned_containers,
            containers_with_charges=containers_with_charges,
            average_dwell_time_days=float(average_dwell),
            on_time_return_rate=float(on_time_rate),
            period_start=start_date,
            period_end=end_date,
        )
    
    def get_customer_metrics(
        self,
        customer_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Optional[CustomerMetrics]:
        """
        Get metrics for specific customer.
        
        Args:
            customer_id: Customer ID
            start_date: Optional start date (defaults to 90 days ago)
            end_date: Optional end date (defaults to today)
            
        Returns:
            CustomerMetrics or None if customer not found
        """
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            return None
        
        if end_date is None:
            end_date = date.today()
        
        if start_date is None:
            start_date = end_date - timedelta(days=90)
        
        logger.info(
            f"Calculating metrics for customer {customer.name} "
            f"from {start_date} to {end_date}"
        )
        
        # Get loads
        loads = self.db.query(Load).filter(
            and_(
                Load.customer_id == customer_id,
                Load.created_at >= datetime.combine(start_date, datetime.min.time()),
                Load.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        ).all()
        
        total_loads = len(loads)
        
        # Get invoices
        invoices = self.db.query(Invoice).filter(
            and_(
                Invoice.customer_id == customer_id,
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date
            )
        ).all()
        
        total_invoiced = sum(inv.total_amount for inv in invoices)
        
        total_paid = sum(
            inv.amount_paid for inv in invoices
            if inv.amount_paid
        )
        
        outstanding_balance = sum(
            inv.total_amount - (inv.amount_paid or 0)
            for inv in invoices
            if inv.status != InvoiceStatus.PAID
        )
        
        # Calculate average payment days
        payment_days = []
        for inv in invoices:
            if inv.status == InvoiceStatus.PAID and inv.paid_date and inv.invoice_date:
                days = (inv.paid_date - inv.invoice_date).days
                payment_days.append(days)
        
        average_payment = (
            sum(payment_days) / len(payment_days) if payment_days else 0.0
        )
        
        # Calculate dispute rate
        disputed = sum(
            1 for inv in invoices if inv.status == InvoiceStatus.DISPUTED
        )
        
        dispute_rate = (
            (disputed / len(invoices) * 100) if invoices else 0.0
        )
        
        # Calculate on-time payment rate
        on_time_payments = sum(
            1 for inv in invoices
            if inv.status == InvoiceStatus.PAID
            and inv.paid_date
            and inv.due_date
            and inv.paid_date <= inv.due_date
        )
        
        paid_count = sum(
            1 for inv in invoices if inv.status == InvoiceStatus.PAID
        )
        
        on_time_rate = (
            (on_time_payments / paid_count * 100) if paid_count > 0 else 0.0
        )
        
        return CustomerMetrics(
            customer_name=customer.name,
            total_loads=total_loads,
            total_invoiced=float(total_invoiced),
            total_paid=float(total_paid),
            outstanding_balance=float(outstanding_balance),
            average_payment_days=float(average_payment),
            dispute_rate=float(dispute_rate),
            on_time_payment_rate=float(on_time_rate),
        )
    
    def get_top_customers_by_revenue(
        self,
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top customers by revenue in date range.
        
        Args:
            start_date: Start date
            end_date: End date
            limit: Number of customers to return
            
        Returns:
            List of customer revenue data
        """
        results = self.db.query(
            Customer.name,
            func.sum(Invoice.total_amount).label('total_revenue'),
            func.count(Invoice.id).label('invoice_count')
        ).join(
            Invoice, Invoice.customer_id == Customer.id
        ).filter(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date
            )
        ).group_by(
            Customer.id, Customer.name
        ).order_by(
            func.sum(Invoice.total_amount).desc()
        ).limit(limit).all()
        
        return [
            {
                "customer_name": name,
                "total_revenue": float(revenue),
                "invoice_count": count,
            }
            for name, revenue, count in results
        ]
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """
        Get overall system health metrics.
        
        Returns:
            System health metrics
        """
        logger.info("Calculating system health metrics")
        
        # Count active entities
        total_customers = self.db.query(Customer).filter(
            Customer.active == True
        ).count()
        
        active_loads = self.db.query(Load).filter(
            Load.actual_delivery_date.is_(None)
        ).count()
        
        active_containers = self.db.query(Container).filter(
            Container.returned_empty.is_(None)
        ).count()
        
        pending_invoices = self.db.query(Invoice).filter(
            Invoice.status.in_([
                InvoiceStatus.PENDING_APPROVAL,
                InvoiceStatus.SENT,
                InvoiceStatus.OVERDUE,
            ])
        ).count()
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        
        recent_invoices = self.db.query(Invoice).filter(
            Invoice.created_at >= yesterday
        ).count()
        
        recent_loads = self.db.query(Load).filter(
            Load.created_at >= yesterday
        ).count()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_customers": total_customers,
            "active_loads": active_loads,
            "active_containers": active_containers,
            "pending_invoices": pending_invoices,
            "recent_invoices_24h": recent_invoices,
            "recent_loads_24h": recent_loads,
        }


def get_metrics_collector(db: Session) -> MetricsCollector:
    """
    Get metrics collector instance.
    
    Args:
        db: Database session
        
    Returns:
        MetricsCollector instance
    """
    return MetricsCollector(db)

