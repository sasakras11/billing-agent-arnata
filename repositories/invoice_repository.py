"""Repository for invoice operations."""
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models import Invoice, InvoiceStatus
from repositories.base import BaseRepository
from logging_config import get_logger

logger = get_logger(__name__)


class InvoiceRepository(BaseRepository[Invoice]):
    """Repository for invoice-specific database operations."""
    
    def __init__(self, db: Session):
        """
        Initialize invoice repository.
        
        Args:
            db: Database session
        """
        super().__init__(Invoice, db)
    
    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """
        Get invoice by invoice number.
        
        Args:
            invoice_number: Invoice number
            
        Returns:
            Invoice or None
        """
        return self.db.query(Invoice).filter(
            Invoice.invoice_number == invoice_number
        ).first()
    
    def get_by_customer(
        self,
        customer_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """
        Get invoices for a customer.
        
        Args:
            customer_id: Customer ID
            skip: Pagination offset
            limit: Page size
            
        Returns:
            List of invoices
        """
        return self.db.query(Invoice).filter(
            Invoice.customer_id == customer_id
        ).order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_by_status(
        self,
        status: InvoiceStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invoice]:
        """
        Get invoices by status.
        
        Args:
            status: Invoice status
            skip: Pagination offset
            limit: Page size
            
        Returns:
            List of invoices
        """
        return self.db.query(Invoice).filter(
            Invoice.status == status
        ).order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_overdue_invoices(self, as_of_date: Optional[date] = None) -> List[Invoice]:
        """
        Get all overdue invoices.
        
        Args:
            as_of_date: Check overdue as of this date (default: today)
            
        Returns:
            List of overdue invoices
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        return self.db.query(Invoice).filter(
            and_(
                Invoice.due_date < as_of_date,
                Invoice.status != InvoiceStatus.PAID,
                Invoice.status != InvoiceStatus.VOIDED
            )
        ).order_by(Invoice.due_date.asc()).all()
    
    def get_disputed_invoices(self) -> List[Invoice]:
        """
        Get all disputed invoices.
        
        Returns:
            List of disputed invoices
        """
        return self.db.query(Invoice).filter(
            Invoice.status == InvoiceStatus.DISPUTED
        ).order_by(Invoice.created_at.desc()).all()
    
    def get_pending_payment_invoices(self) -> List[Invoice]:
        """
        Get invoices pending payment.
        
        Returns:
            List of pending invoices
        """
        return self.db.query(Invoice).filter(
            or_(
                Invoice.status == InvoiceStatus.SENT,
                Invoice.status == InvoiceStatus.PENDING
            )
        ).order_by(Invoice.due_date.asc()).all()
    
    def get_by_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[Invoice]:
        """
        Get invoices created within date range.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of invoices
        """
        return self.db.query(Invoice).filter(
            and_(
                Invoice.invoice_date >= start_date,
                Invoice.invoice_date <= end_date
            )
        ).order_by(Invoice.invoice_date.desc()).all()
    
    def get_unpaid_total_by_customer(self, customer_id: int) -> float:
        """
        Get total unpaid amount for a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            Total unpaid amount
        """
        from sqlalchemy import func
        
        result = self.db.query(
            func.sum(Invoice.total_amount - Invoice.amount_paid)
        ).filter(
            and_(
                Invoice.customer_id == customer_id,
                Invoice.status != InvoiceStatus.PAID,
                Invoice.status != InvoiceStatus.VOIDED
            )
        ).scalar()
        
        return float(result) if result else 0.0
    
    def mark_as_paid(
        self,
        invoice_id: int,
        payment_date: Optional[date] = None,
        payment_method: Optional[str] = None
    ) -> Optional[Invoice]:
        """
        Mark invoice as paid.
        
        Args:
            invoice_id: Invoice ID
            payment_date: Payment date (default: today)
            payment_method: Payment method
            
        Returns:
            Updated invoice or None
        """
        invoice = self.get_by_id(invoice_id)
        
        if not invoice:
            return None
        
        if payment_date is None:
            payment_date = date.today()
        
        invoice.status = InvoiceStatus.PAID
        invoice.amount_paid = invoice.total_amount
        invoice.paid_date = payment_date
        
        if payment_method:
            invoice.payment_method = payment_method
        
        self.db.commit()
        self.db.refresh(invoice)
        
        logger.info(f"Marked invoice {invoice.invoice_number} as paid")
        return invoice
    
    def get_by_load(self, load_id: int) -> List[Invoice]:
        """Get distinct invoices that have charges linked to a load."""
        from models import Charge
        return (
            self.db.query(Invoice)
            .join(Charge, Charge.invoice_id == Invoice.id)
            .filter(Charge.load_id == load_id)
            .distinct()
            .all()
        )

    def mark_as_sent(self, invoice_id: int) -> Optional[Invoice]:
        """
        Mark invoice as sent.
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Updated invoice or None
        """
        return self.update(invoice_id, status=InvoiceStatus.SENT)

