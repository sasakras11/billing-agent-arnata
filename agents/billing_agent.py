"""Simple billing agent for invoice generation."""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from models import Load, Invoice
from services.charge_calculator import ChargeCalculator
from services.invoice_generator import InvoiceGenerator

logger = logging.getLogger(__name__)


class BillingAgent:
    """Simple billing agent for automated invoicing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.charge_calculator = ChargeCalculator(db)
        self.invoice_generator = InvoiceGenerator(db)
    
    def process_load_billing(self, load: Load) -> Optional[Invoice]:
        """Process billing for a completed load."""
        try:
            # Calculate charges
            charges = self.charge_calculator.calculate_all_charges(load)
            if not charges:
                return None
            
            # Save charges
            for charge in charges:
                self.db.add(charge)
            self.db.commit()
            
            # Generate invoice if auto-invoice enabled
            if not load.customer.auto_invoice:
                return None
            
            invoice = self.invoice_generator.create_invoice_from_load(
                load=load, charges=charges, auto_send=True
            )
            
            # Sync to QuickBooks if configured
            if invoice and load.customer.quickbooks_customer_id:
                self.invoice_generator.sync_to_quickbooks(invoice)
            
            return invoice
            
        except Exception as e:
            logger.error(f"Error processing load {load.id}: {e}")
            self.db.rollback()
            return None

