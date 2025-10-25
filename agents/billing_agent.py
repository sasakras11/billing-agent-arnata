"""AI Agent for billing and invoice generation - MVP Version."""
import logging
from datetime import datetime
from typing import List, Optional

from langchain_anthropic import ChatAnthropic
from sqlalchemy.orm import Session

from models import Load, Customer, Charge, Invoice
from services.charge_calculator import ChargeCalculator
from services.invoice_generator import InvoiceGenerator
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BillingAgent:
    """AI Agent for automated billing and invoicing - MVP core functions only."""
    
    def __init__(self, db: Session):
        """Initialize billing agent with essential services."""
        self.db = db
        self.charge_calculator = ChargeCalculator(db)
        self.invoice_generator = InvoiceGenerator(db)
        
        # Initialize Claude LLM
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.3,
        )
    
    async def process_load_billing(self, load: Load) -> Optional[Invoice]:
        """
        Process billing for a completed load (MVP core flow).
        
        Args:
            load: Load object
            
        Returns:
            Invoice object or None
        """
        try:
            logger.info(f"Processing billing for load {load.id}")
            
            # Calculate charges
            charges = self.charge_calculator.calculate_all_charges(load)
            if not charges:
                logger.warning(f"No charges for load {load.id}")
                return None
            
            # AI validation
            if not await self.validate_charges(load, charges):
                logger.warning(f"Charges rejected by AI for load {load.id}")
                return None
            
            # Save charges
            for charge in charges:
                self.db.add(charge)
            self.db.commit()
            
            # Generate invoice if customer has auto_invoice enabled
            if load.customer.auto_invoice:
                invoice = self.invoice_generator.create_invoice_from_load(
                    load=load,
                    charges=charges,
                    auto_send=True
                )
                
                # Sync to QuickBooks if configured
                if invoice and load.customer.quickbooks_customer_id:
                    self.invoice_generator.sync_to_quickbooks(invoice)
                
                logger.info(f"Invoice {invoice.invoice_number} created for load {load.id}")
                return invoice
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing billing: {e}")
            self.db.rollback()
            return None
    
    async def validate_charges(self, load: Load, charges: List[Charge]) -> bool:
        """
        AI validation of calculated charges.
        
        Args:
            load: Load object
            charges: List of calculated charges
            
        Returns:
            True if approved, False otherwise
        """
        try:
            # Prepare charge summary
            charges_summary = [
                f"{c.charge_type.value}: ${c.amount:.2f} ({c.quantity} x ${c.rate:.2f})"
                for c in charges
            ]
            total = sum(c.amount for c in charges)
            
            # Simple AI validation prompt
            prompt = f"""Review these trucking charges for reasonableness:
            
Load: {load.mcleod_load_number}
Base Rate: ${load.base_freight_rate or 0:.2f}
Charges:
{chr(10).join(charges_summary)}
Total: ${total:.2f}

Respond APPROVED or REJECTED with brief reasoning."""
            
            response = await self.llm.ainvoke([{"role": "user", "content": prompt}])
            approved = "APPROVED" in response.content.upper()[:50]
            
            logger.info(f"Charge validation for load {load.id}: {'APPROVED' if approved else 'REJECTED'}")
            return approved
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

