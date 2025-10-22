"""Invoice generation service."""
import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session

from models import Invoice, InvoiceStatus, InvoiceLineItem, Charge, Load, Customer
from integrations.quickbooks_client import QuickBooksClient, QBLineItem
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class InvoiceGenerator:
    """Generate and manage invoices."""
    
    def __init__(self, db: Session, qb_client: Optional[QuickBooksClient] = None):
        """
        Initialize invoice generator.
        
        Args:
            db: Database session
            qb_client: Optional QuickBooks client (for testing)
        """
        self.db = db
        self.qb_client = qb_client or QuickBooksClient()
    
    def create_invoice_from_load(
        self,
        load: Load,
        charges: List[Charge],
        auto_send: bool = False
    ) -> Optional[Invoice]:
        """
        Create invoice from load and charges.
        
        Args:
            load: Load object
            charges: List of charges to include
            auto_send: Automatically send to customer
            
        Returns:
            Invoice object or None
        """
        try:
            customer = load.customer
            
            if not customer:
                logger.error(f"Load {load.id} has no customer")
                return None
            
            # Calculate totals
            subtotal = sum(charge.amount for charge in charges if charge.is_billable)
            tax_amount = 0.0  # Add tax calculation if needed
            total_amount = subtotal + tax_amount
            
            # Generate invoice number
            invoice_date = date.today()
            invoice_number = self._generate_invoice_number(customer, invoice_date)
            
            # Calculate due date based on payment terms
            due_date = self._calculate_due_date(customer.payment_terms, invoice_date)
            
            # Create invoice record
            invoice = Invoice(
                invoice_number=invoice_number,
                customer_id=customer.id,
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_amount=total_amount,
                balance_due=total_amount,
                invoice_date=invoice_date,
                due_date=due_date,
                status=InvoiceStatus.DRAFT,
                payment_terms=customer.payment_terms,
                memo=f"Invoice for Load {load.mcleod_load_number} - Container {load.container_number}",
                ai_generated=True,
                requires_human_review=self._requires_review(charges),
            )
            
            self.db.add(invoice)
            self.db.flush()  # Get invoice.id
            
            # Create line items
            line_items = []
            for idx, charge in enumerate(charges, 1):
                if not charge.is_billable:
                    continue
                
                line_item = InvoiceLineItem(
                    invoice_id=invoice.id,
                    item_number=idx,
                    description=charge.description,
                    quantity=charge.quantity,
                    unit_price=charge.rate,
                    amount=charge.amount,
                )
                line_items.append(line_item)
                
                # Link charge to invoice
                charge.invoice_id = invoice.id
            
            self.db.add_all(line_items)
            
            # Update invoice relationship
            invoice.line_items = line_items
            invoice.charges = charges
            
            self.db.commit()
            
            logger.info(
                f"Created invoice {invoice_number} for load {load.id}, "
                f"total: ${total_amount:.2f}"
            )
            
            # Auto-send if requested
            if auto_send and customer.auto_invoice:
                self.send_to_customer(invoice)
            
            return invoice
            
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            self.db.rollback()
            return None
    
    def sync_to_quickbooks(self, invoice: Invoice) -> bool:
        """
        Sync invoice to QuickBooks.
        
        Args:
            invoice: Invoice object
            
        Returns:
            True if successful
        """
        try:
            customer = invoice.customer
            
            # Ensure customer exists in QuickBooks
            if not customer.quickbooks_customer_id:
                logger.warning(f"Customer {customer.id} not in QuickBooks, skipping sync")
                return False
            
            # Build line items for QuickBooks
            qb_line_items = []
            for line_item in invoice.line_items:
                qb_line_items.append(
                    QBLineItem(
                        description=line_item.description,
                        quantity=line_item.quantity,
                        unit_price=line_item.unit_price,
                        amount=line_item.amount,
                    )
                )
            
            # Create invoice in QuickBooks
            qb_invoice = self.qb_client.create_invoice(
                customer_id=customer.quickbooks_customer_id,
                line_items=qb_line_items,
                invoice_date=invoice.invoice_date,
                due_date=invoice.due_date,
                doc_number=invoice.invoice_number,
                memo=invoice.memo,
            )
            
            if qb_invoice:
                # Update invoice with QuickBooks data
                invoice.quickbooks_invoice_id = qb_invoice.id
                invoice.quickbooks_sync_token = qb_invoice.sync_token
                invoice.status = InvoiceStatus.APPROVED
                self.db.commit()
                
                logger.info(f"Synced invoice {invoice.invoice_number} to QuickBooks")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error syncing invoice to QuickBooks: {e}")
            return False
    
    def send_to_customer(self, invoice: Invoice) -> bool:
        """
        Send invoice to customer via QuickBooks.
        
        Args:
            invoice: Invoice object
            
        Returns:
            True if successful
        """
        try:
            if not invoice.quickbooks_invoice_id:
                # Sync to QuickBooks first
                if not self.sync_to_quickbooks(invoice):
                    logger.error("Failed to sync invoice before sending")
                    return False
            
            # Send via QuickBooks
            customer = invoice.customer
            success = self.qb_client.send_invoice(
                invoice_id=invoice.quickbooks_invoice_id,
                email_address=customer.email or customer.alert_email,
            )
            
            if success:
                invoice.status = InvoiceStatus.SENT
                invoice.sent_date = date.today()
                self.db.commit()
                
                logger.info(f"Sent invoice {invoice.invoice_number} to customer")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending invoice: {e}")
            return False
    
    def check_payment_status(self, invoice: Invoice) -> bool:
        """
        Check payment status from QuickBooks.
        
        Args:
            invoice: Invoice object
            
        Returns:
            True if status was updated
        """
        try:
            if not invoice.quickbooks_invoice_id:
                return False
            
            # Get latest invoice data from QuickBooks
            qb_invoice = self.qb_client.get_invoice(invoice.quickbooks_invoice_id)
            
            if not qb_invoice:
                return False
            
            # Update invoice status
            old_balance = invoice.balance_due
            invoice.balance_due = qb_invoice.balance
            invoice.amount_paid = qb_invoice.total_amount - qb_invoice.balance
            
            # Update status based on balance
            if qb_invoice.balance == 0:
                invoice.status = InvoiceStatus.PAID
                invoice.paid_date = date.today()
            elif qb_invoice.balance < qb_invoice.total_amount:
                invoice.status = InvoiceStatus.PARTIALLY_PAID
                
                # Check for short payment (dispute)
                if qb_invoice.balance > 0 and old_balance > qb_invoice.balance:
                    self._handle_short_payment(invoice, old_balance, qb_invoice.balance)
            elif invoice.due_date and date.today() > invoice.due_date:
                invoice.status = InvoiceStatus.OVERDUE
            
            invoice.quickbooks_sync_token = qb_invoice.sync_token
            self.db.commit()
            
            logger.info(f"Updated invoice {invoice.invoice_number} status: {invoice.status}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return False
    
    def _generate_invoice_number(
        self,
        customer: Customer,
        invoice_date: date
    ) -> str:
        """Generate unique invoice number."""
        # Format: INV-YYYYMM-XXXXX
        prefix = f"INV-{invoice_date.strftime('%Y%m')}"
        
        # Find highest invoice number for this month
        last_invoice = (
            self.db.query(Invoice)
            .filter(Invoice.invoice_number.like(f"{prefix}-%"))
            .order_by(Invoice.invoice_number.desc())
            .first()
        )
        
        if last_invoice:
            # Extract sequence number
            try:
                last_seq = int(last_invoice.invoice_number.split("-")[-1])
                seq = last_seq + 1
            except:
                seq = 1
        else:
            seq = 1
        
        return f"{prefix}-{seq:05d}"
    
    def _calculate_due_date(
        self,
        payment_terms: str,
        invoice_date: date
    ) -> date:
        """Calculate due date from payment terms."""
        # Parse payment terms (e.g., "Net 30", "Net 15", "Due on Receipt")
        if "Due on Receipt" in payment_terms:
            return invoice_date
        
        try:
            # Extract number of days
            days = int(payment_terms.split()[-1])
            return invoice_date + timedelta(days=days)
        except:
            # Default to 30 days
            return invoice_date + timedelta(days=30)
    
    def _requires_review(self, charges: List[Charge]) -> bool:
        """Check if invoice requires human review."""
        # Review if:
        # - Low AI confidence on any charge
        # - Very high total amount
        # - Disputed charges
        
        for charge in charges:
            if charge.ai_confidence_score and charge.ai_confidence_score < 0.80:
                return True
            if charge.is_disputed:
                return True
        
        total = sum(c.amount for c in charges)
        if total > 5000:  # High value threshold
            return True
        
        return False
    
    def _handle_short_payment(
        self,
        invoice: Invoice,
        old_balance: float,
        new_balance: float
    ):
        """Handle short payment (potential dispute)."""
        try:
            short_amount = old_balance - new_balance - (invoice.amount_paid or 0)
            
            if short_amount > 10:  # Ignore small discrepancies
                invoice.is_disputed = True
                invoice.dispute_amount = short_amount
                invoice.status = InvoiceStatus.DISPUTED
                
                logger.warning(
                    f"Invoice {invoice.invoice_number} short paid by ${short_amount:.2f}"
                )
                
        except Exception as e:
            logger.error(f"Error handling short payment: {e}")

