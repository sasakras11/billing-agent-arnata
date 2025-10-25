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
    
    async def validate_charges(
        self,
        load: Load,
        charges: List[Charge]
    ) -> Dict[str, Any]:
        """
        Use AI to validate calculated charges.
        
        Args:
            load: Load object
            charges: List of calculated charges
            
        Returns:
            Validation result dictionary
        """
        try:
            # Prepare data for AI
            load_data = {
                "load_number": load.mcleod_load_number,
                "container_number": load.container_number,
                "pickup_date": load.pickup_date.isoformat() if load.pickup_date else None,
                "delivery_date": load.actual_delivery_date.isoformat() if load.actual_delivery_date else None,
                "base_freight_rate": float(load.base_freight_rate) if load.base_freight_rate else 0,
            }
            
            charges_data = []
            for charge in charges:
                charges_data.append({
                    "type": charge.charge_type.value,
                    "description": charge.description,
                    "rate": float(charge.rate),
                    "quantity": float(charge.quantity),
                    "amount": float(charge.amount),
                    "confidence": float(charge.ai_confidence_score) if charge.ai_confidence_score else 0,
                })
            
            total_amount = sum(c.amount for c in charges)
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are an expert billing auditor for trucking and logistics.
                Review the calculated charges for accuracy and reasonableness.
                Consider:
                - Are the charge types appropriate?
                - Are the rates reasonable for industry standards?
                - Are the quantities (days, etc.) calculated correctly?
                - Is the total amount reasonable for this type of load?
                - Are there any red flags or unusual patterns?
                
                Respond with:
                - APPROVED or REJECTED
                - Detailed reasoning
                - Any concerns or recommendations
                """),
                HumanMessage(content=f"""
                Load: {load_data}
                Charges: {charges_data}
                Total Amount: ${total_amount:.2f}
                
                Please validate these charges.
                """)
            ])
            
            # Get AI validation
            response = await self.llm.ainvoke(prompt.format_messages())
            
            content = response.content.upper()
            approved = "APPROVED" in content[:100] and "REJECTED" not in content[:100]
            
            validation = {
                "approved": approved,
                "reasoning": response.content,
                "total_amount": total_amount,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"AI validation for load {load.id}: "
                f"{'APPROVED' if approved else 'REJECTED'}"
            )
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validating charges: {e}")
            return {
                "approved": False,
                "reason": f"Validation error: {str(e)}",
            }
    
    async def analyze_billing_patterns(
        self,
        customer: Customer,
        days: int = 90
    ) -> Dict[str, Any]:
        """
        Analyze billing patterns for customer.
        
        Args:
            customer: Customer object
            days: Number of days to analyze
            
        Returns:
            Analysis dictionary
        """
        try:
            from datetime import timedelta
            
            # Get recent loads
            since_date = date.today() - timedelta(days=days)
            loads = (
                self.db.query(Load)
                .filter(
                    Load.customer_id == customer.id,
                    Load.created_at >= since_date
                )
                .all()
            )
            
            # Calculate statistics
            total_loads = len(loads)
            total_containers = sum(1 for l in loads if l.container)
            
            # Get charges
            all_charges = []
            for load in loads:
                all_charges.extend(load.charges)
            
            per_diem_charges = [c for c in all_charges if c.charge_type.value == "per_diem"]
            demurrage_charges = [c for c in all_charges if c.charge_type.value == "demurrage"]
            detention_charges = [c for c in all_charges if c.charge_type.value == "detention"]
            
            total_per_diem = sum(c.amount for c in per_diem_charges)
            total_demurrage = sum(c.amount for c in demurrage_charges)
            total_detention = sum(c.amount for c in detention_charges)
            
            # Get invoices
            invoices = (
                self.db.query(Invoice)
                .filter(
                    Invoice.customer_id == customer.id,
                    Invoice.invoice_date >= since_date
                )
                .all()
            )
            
            total_invoiced = sum(i.total_amount for i in invoices)
            total_paid = sum(i.amount_paid for i in invoices if i.amount_paid)
            
            # Prepare data for AI
            analysis_data = {
                "customer_name": customer.name,
                "period_days": days,
                "total_loads": total_loads,
                "total_containers": total_containers,
                "per_diem_charges": f"${total_per_diem:.2f} ({len(per_diem_charges)} instances)",
                "demurrage_charges": f"${total_demurrage:.2f} ({len(demurrage_charges)} instances)",
                "detention_charges": f"${total_detention:.2f} ({len(detention_charges)} instances)",
                "total_invoiced": f"${total_invoiced:.2f}",
                "total_paid": f"${total_paid:.2f}",
                "payment_rate": f"{(total_paid / total_invoiced * 100) if total_invoiced > 0 else 0:.1f}%",
            }
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are a logistics business analyst.
                Analyze the billing patterns and provide insights:
                - Identify trends and patterns
                - Calculate ROI and savings opportunities
                - Recommend process improvements
                - Highlight concerns or risks
                
                Provide actionable recommendations for the customer."""),
                HumanMessage(content=f"Analyze billing patterns: {analysis_data}")
            ])
            
            # Get AI analysis
            response = await self.llm.ainvoke(prompt.format_messages())
            
            analysis = {
                **analysis_data,
                "ai_insights": response.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Completed billing analysis for customer {customer.id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing billing patterns: {e}")
            return {"error": str(e)}
    
    async def recommend_rate_optimization(
        self,
        customer: Customer
    ) -> Dict[str, Any]:
        """
        AI recommendations for rate optimization.
        
        Args:
            customer: Customer object
            
        Returns:
            Recommendations dictionary
        """
        try:
            # Get customer rates
            rates = {
                "per_diem_rate": float(customer.per_diem_rate),
                "demurrage_rate": float(customer.demurrage_rate),
                "detention_rate": float(customer.detention_rate),
                "free_days": customer.free_days,
            }
            
            # Industry averages
            industry_avg = {
                "per_diem_rate": settings.default_per_diem_rate,
                "demurrage_rate": settings.default_demurrage_rate,
                "detention_rate": settings.default_detention_rate,
                "free_days": settings.default_free_days,
            }
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are a pricing strategy expert for trucking and logistics.
                Compare customer rates to industry averages and recommend optimizations.
                Consider:
                - Competitive positioning
                - Profitability
                - Customer retention vs revenue optimization
                - Market conditions
                
                Provide specific rate recommendations with reasoning."""),
                HumanMessage(content=f"""
                Customer: {customer.name}
                Current Rates: {rates}
                Industry Averages: {industry_avg}
                
                What rate optimizations do you recommend?
                """)
            ])
            
            # Get AI recommendations
            response = await self.llm.ainvoke(prompt.format_messages())
            
            recommendations = {
                "customer_name": customer.name,
                "current_rates": rates,
                "industry_averages": industry_avg,
                "recommendations": response.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Generated rate recommendations for customer {customer.id}")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating rate recommendations: {e}")
            return {"error": str(e)}
    
    def get_billing_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get billing metrics for dashboard.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Metrics dictionary
        """
        try:
            from datetime import timedelta
            
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Get invoices
            invoices = (
                self.db.query(Invoice)
                .filter(Invoice.created_at >= since_date)
                .all()
            )
            
            # Calculate metrics
            total_invoices = len(invoices)
            ai_generated = sum(1 for i in invoices if i.ai_generated)
            auto_sent = sum(1 for i in invoices if i.status == InvoiceStatus.SENT)
            total_revenue = sum(i.total_amount for i in invoices)
            collected_revenue = sum(i.amount_paid for i in invoices if i.amount_paid)
            
            # Get charges
            charges = (
                self.db.query(Charge)
                .filter(Charge.created_at >= since_date)
                .all()
            )
            
            per_diem_total = sum(
                c.amount for c in charges 
                if c.charge_type.value == "per_diem"
            )
            demurrage_total = sum(
                c.amount for c in charges 
                if c.charge_type.value == "demurrage"
            )
            detention_total = sum(
                c.amount for c in charges 
                if c.charge_type.value == "detention"
            )
            
            metrics = {
                "period_days": days,
                "total_invoices": total_invoices,
                "ai_generated_pct": f"{(ai_generated / total_invoices * 100) if total_invoices > 0 else 0:.1f}%",
                "auto_sent_pct": f"{(auto_sent / total_invoices * 100) if total_invoices > 0 else 0:.1f}%",
                "total_revenue": f"${total_revenue:.2f}",
                "collected_revenue": f"${collected_revenue:.2f}",
                "collection_rate": f"{(collected_revenue / total_revenue * 100) if total_revenue > 0 else 0:.1f}%",
                "per_diem_revenue": f"${per_diem_total:.2f}",
                "demurrage_revenue": f"${demurrage_total:.2f}",
                "detention_revenue": f"${detention_total:.2f}",
                "accessorial_revenue": f"${per_diem_total + demurrage_total + detention_total:.2f}",
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating billing metrics: {e}")
            return {"error": str(e)}

