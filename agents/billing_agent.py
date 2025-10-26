"""AI Agent for billing and invoice generation."""
import logging
from typing import List, Optional

from langchain_anthropic import ChatAnthropic
from sqlalchemy.orm import Session

from models import Load, Charge, Invoice
from services.charge_calculator import ChargeCalculator
from services.invoice_generator import InvoiceGenerator
from config import get_settings

logger = logging.getLogger(__name__)


class BillingAgent:
    """AI-powered billing agent for automated invoicing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.charge_calculator = ChargeCalculator(db)
        self.invoice_generator = InvoiceGenerator(db)
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            anthropic_api_key=get_settings().anthropic_api_key,
            temperature=0.3,
        )
    
    async def process_load_billing(self, load: Load) -> Optional[Invoice]:
        """Process billing for a completed load."""
        try:
            # Calculate and validate charges
            charges = self.charge_calculator.calculate_all_charges(load)
            if not charges or not await self.validate_charges(load, charges):
                return None
            
            # Save charges to database
            for charge in charges:
                self.db.add(charge)
            self.db.commit()
            
            # Generate invoice if auto-invoicing is enabled
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
    
    async def validate_charges(self, load: Load, charges: List[Charge]) -> bool:
        """AI validation of calculated charges."""
        charges_summary = "\n".join([
            f"{c.charge_type.value}: ${c.amount:.2f}"
            for c in charges
        ])
        total = sum(c.amount for c in charges)
        
        prompt = f"""Review these charges for load {load.mcleod_load_number}:
{charges_summary}
Total: ${total:.2f}
Base Rate: ${load.base_freight_rate or 0:.2f}

Reply APPROVED or REJECTED."""
        
        response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
        return "APPROVED" in response.content.upper()[:50]

