"""Billing Agent: charge calculation, invoice generation, and QuickBooks sync."""
import logging
import time
from typing import Optional, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from models import Load, Invoice, Charge, ChargeType
from services.charge_calculator import ChargeCalculator
from services.invoice_generator import InvoiceGenerator
from repositories.invoice_repository import InvoiceRepository
from exceptions import (
    ChargeCalculationError,
    InvoiceGenerationError,
    QuickBooksAPIError,
    DatabaseError,
)

logger = logging.getLogger(__name__)


class BillingAgent:
    """Agent responsible for processing load billing and invoice generation."""
    
    def __init__(self, db: Session):
        """
        Initialize billing agent.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.charge_calculator = ChargeCalculator(db)
        self.invoice_generator = InvoiceGenerator(db)
        self.invoice_repo = InvoiceRepository(db)
    
    def process_load_billing(
        self,
        load: Load,
        auto_send: bool = True
    ) -> Optional[Invoice]:
        """
        Process billing for a load by calculating charges and generating an invoice.
        
        This method:
        1. Calculates all applicable charges for the load
        2. Saves charges to database
        3. Generates invoice if customer has auto-invoicing enabled
        4. Syncs invoice to QuickBooks if customer is configured
        
        Args:
            load: The load to process billing for
            auto_send: Whether to automatically send invoice to customer
            
        Returns:
            Invoice if generated, None otherwise
            
        Raises:
            ChargeCalculationError: If charge calculation fails
            InvoiceGenerationError: If invoice generation fails
            DatabaseError: If database operations fail
        """
        start_time = time.time()
        logger.info(f"Processing billing for load {load.id}")
        
        try:
            # Calculate all charges
            charges = self._calculate_charges(load)
            
            # Save charges to database
            if charges:
                self._save_charges(charges)
                logger.info(
                    f"Saved {len(charges)} charges for load {load.id}, "
                    f"total: ${sum(c.amount for c in charges):.2f}"
                )
            else:
                logger.warning(f"No charges calculated for load {load.id}")
            
            # Check if customer wants auto-invoicing
            if not load.customer.auto_invoice:
                logger.info(
                    f"Auto-invoicing disabled for customer {load.customer.name}"
                )
                return None
            
            # Generate invoice
            invoice = self._generate_invoice(load, charges, auto_send)
            
            # Sync to QuickBooks if configured
            if invoice and load.customer.quickbooks_customer_id:
                self._sync_to_quickbooks(invoice)
            
            elapsed_time = time.time() - start_time
            logger.info(
                f"Successfully processed billing for load {load.id}, "
                f"invoice: {invoice.id if invoice else 'N/A'}, "
                f"elapsed: {elapsed_time:.2f}s"
            )
            
            return invoice
            
        except (ChargeCalculationError, InvoiceGenerationError) as e:
            # Expected errors - already logged, just re-raise
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error processing load {load.id}: {e}")
            raise DatabaseError(f"Database error processing load {load.id}") from e
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error processing load {load.id}: {e}", exc_info=True)
            raise
    
    def _calculate_charges(self, load: Load) -> list[Charge]:
        """Calculate all charges for a load."""
        try:
            return self.charge_calculator.calculate_all_charges(load)
        except Exception as e:
            logger.error(f"Failed to calculate charges for load {load.id}: {e}")
            raise ChargeCalculationError(f"Failed to calculate charges for load {load.id}") from e
    
    def _save_charges(self, charges: list[Charge]) -> None:
        """Save charges to database."""
        try:
            self.db.add_all(charges)
            self.db.commit()
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to save charges: {e}")
            raise DatabaseError("Failed to save charges") from e
    
    def _generate_invoice(self, load: Load, charges: list[Charge], auto_send: bool) -> Optional[Invoice]:
        """Generate invoice for load and charges."""
        try:
            return self.invoice_generator.create_invoice_from_load(load, charges, auto_send=auto_send)
        except Exception as e:
            logger.error(f"Failed to generate invoice for load {load.id}: {e}")
            raise InvoiceGenerationError(f"Failed to generate invoice for load {load.id}") from e
    
    def _sync_to_quickbooks(self, invoice: Invoice) -> None:
        """Sync invoice to QuickBooks."""
        try:
            self.invoice_generator.sync_to_quickbooks(invoice)
            logger.info(f"Synced invoice {invoice.id} to QuickBooks")
        except Exception as e:
            logger.error(f"Failed to sync invoice {invoice.id} to QuickBooks: {e}", exc_info=True)
            raise QuickBooksAPIError(f"Failed to sync invoice {invoice.id} to QuickBooks") from e
    
    def preview_charges(self, load: Load) -> Dict[str, Any]:
        """
        Preview charges for a load without saving to database.
        
        Args:
            load: Load to preview charges for
            
        Returns:
            Dictionary containing charge preview information
            
        Raises:
            ChargeCalculationError: If charge calculation fails
        """
        logger.info(f"Previewing charges for load {load.id}")
        
        try:
            charges = self._calculate_charges(load)
            
            # Organize charges by type
            charges_by_type = {}
            total_amount = Decimal('0.00')
            
            for charge in charges:
                charge_type = getattr(charge.charge_type, 'value', str(charge.charge_type))
                if charge_type not in charges_by_type:
                    charges_by_type[charge_type] = []
                charges_by_type[charge_type].append({
                    'description': charge.description,
                    'rate': float(charge.rate),
                    'quantity': float(charge.quantity),
                    'amount': float(charge.amount),
                    'start_date': charge.start_date.isoformat() if charge.start_date else None,
                    'end_date': charge.end_date.isoformat() if charge.end_date else None,
                })
                total_amount += Decimal(str(charge.amount))
            
            preview = {
                'load_id': load.id,
                'customer_name': load.customer.name,
                'customer_id': load.customer.id,
                'container_number': load.container.container_number if load.container else None,
                'charge_count': len(charges),
                'charges_by_type': charges_by_type,
                'total_amount': float(total_amount),
                'auto_invoice_enabled': load.customer.auto_invoice,
                'quickbooks_enabled': bool(load.customer.quickbooks_customer_id),
            }
            
            logger.info(
                f"Preview complete for load {load.id}: "
                f"{len(charges)} charges, total ${total_amount:.2f}"
            )
            
            return preview
            
        except Exception as e:
            logger.error(f"Failed to preview charges for load {load.id}: {e}")
            raise ChargeCalculationError(
                f"Failed to preview charges for load {load.id}"
            ) from e
    
    def get_billing_summary(self, load: Load) -> Dict[str, Any]:
        """Get a comprehensive billing summary for a load."""
        logger.info(f"Getting billing summary for load {load.id}")

        try:
            existing_charges = (
                self.db.query(Charge).filter(Charge.load_id == load.id).all()
            )
            existing_invoices = self.invoice_repo.get_by_load(load.id)
            
            total_charges = sum(c.amount for c in existing_charges)
            total_invoiced = sum(i.total_amount for i in existing_invoices)
            
            summary = {
                'load_id': load.id,
                'customer_name': load.customer.name,
                'status': getattr(load.status, 'value', str(load.status)),
                'charges': {
                    'count': len(existing_charges),
                    'total': float(total_charges),
                    'by_type': self._group_charges_by_type(existing_charges),
                },
                'invoices': {
                    'count': len(existing_invoices),
                    'total': float(total_invoiced),
                    'details': [
                        {
                            'id': inv.id,
                            'number': inv.invoice_number,
                            'amount': float(inv.total_amount),
                            'status': getattr(inv.status, 'value', str(inv.status)),
                            'created_at': inv.created_at.isoformat() if inv.created_at else None,
                        }
                        for inv in existing_invoices
                    ],
                },
                'container': {
                    'number': load.container.container_number if load.container else None,
                    'picked_up': load.container.picked_up.isoformat() if load.container and load.container.picked_up else None,
                    'delivered': load.container.delivered.isoformat() if load.container and load.container.delivered else None,
                },
            }
            
            logger.info(
                f"Billing summary for load {load.id}: "
                f"{len(existing_charges)} charges (${total_charges:.2f}), "
                f"{len(existing_invoices)} invoices (${total_invoiced:.2f})"
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get billing summary for load {load.id}: {e}")
            raise
    
    def _group_charges_by_type(self, charges: list[Charge]) -> Dict[str, Dict[str, Any]]:
        """Group charges by type with totals."""
        grouped = {}
        
        for charge in charges:
            charge_type = getattr(charge.charge_type, 'value', str(charge.charge_type))
            if charge_type not in grouped:
                grouped[charge_type] = {'count': 0, 'total': 0.0}
            grouped[charge_type]['count'] += 1
            grouped[charge_type]['total'] += float(charge.amount)
        
        return grouped

