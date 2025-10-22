"""AI Agent for handling billing disputes."""
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from models import Invoice, Customer, Charge
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DisputeAgent:
    """AI Agent for handling payment disputes and customer communications."""
    
    def __init__(self, db: Session):
        """
        Initialize dispute agent.
        
        Args:
            db: Database session
        """
        self.db = db
        
        # Initialize Claude LLM
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.5,  # Slightly higher for creative email writing
        )
    
    async def draft_dispute_response(
        self,
        invoice: Invoice,
        dispute_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Draft professional email response to disputed invoice.
        
        Args:
            invoice: Invoice object
            dispute_reason: Optional reason provided by customer
            
        Returns:
            Email draft dictionary
        """
        try:
            customer = invoice.customer
            
            # Gather charge details
            charges_detail = []
            for charge in invoice.charges:
                charges_detail.append({
                    "type": charge.charge_type.value,
                    "description": charge.description,
                    "amount": float(charge.amount),
                    "quantity": float(charge.quantity),
                    "rate": float(charge.rate),
                    "start_date": charge.start_date.isoformat() if charge.start_date else None,
                    "end_date": charge.end_date.isoformat() if charge.end_date else None,
                })
            
            dispute_info = {
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name,
                "invoice_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0,
                "dispute_amount": float(invoice.dispute_amount) if invoice.dispute_amount else 0,
                "charges": charges_detail,
                "dispute_reason": dispute_reason or "Not specified",
            }
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are a professional customer service representative for a trucking company.
                Draft a polite, professional email response to a customer who disputed an invoice.
                
                Your email should:
                - Be courteous and understanding
                - Clearly explain each charge with supporting details
                - Reference specific dates, rates, and calculations
                - Provide documentation references (BOL, gate tickets, etc.)
                - Offer to discuss further if needed
                - Maintain professional tone while being firm on valid charges
                
                Format the email with:
                - Subject line
                - Greeting
                - Body (well-structured with clear sections)
                - Professional closing
                """),
                HumanMessage(content=f"""
                Customer disputed invoice details:
                {dispute_info}
                
                Please draft a response email.
                """)
            ])
            
            # Get AI response
            response = await self.llm.ainvoke(prompt.format_messages())
            
            draft = {
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name,
                "email_draft": response.content,
                "generated_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Generated dispute response for invoice {invoice.invoice_number}")
            return draft
            
        except Exception as e:
            logger.error(f"Error drafting dispute response: {e}")
            return {"error": str(e)}
    
    async def analyze_dispute(
        self,
        invoice: Invoice
    ) -> Dict[str, Any]:
        """
        Analyze dispute to determine validity and recommend action.
        
        Args:
            invoice: Disputed invoice
            
        Returns:
            Analysis dictionary
        """
        try:
            customer = invoice.customer
            
            # Gather context
            dispute_context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name,
                "invoice_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0,
                "dispute_amount": float(invoice.dispute_amount) if invoice.dispute_amount else 0,
                "dispute_reason": invoice.dispute_reason,
            }
            
            # Get charge details
            charges_detail = []
            for charge in invoice.charges:
                charges_detail.append({
                    "type": charge.charge_type.value,
                    "description": charge.description,
                    "amount": float(charge.amount),
                    "is_disputed": charge.is_disputed,
                    "confidence": float(charge.ai_confidence_score) if charge.ai_confidence_score else 0,
                })
            
            dispute_context["charges"] = charges_detail
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are a billing dispute analyst for a trucking company.
                Analyze the dispute objectively and determine:
                1. Is the customer's dispute valid or invalid?
                2. Which specific charges are questionable?
                3. What action should be taken? (write off, negotiate, stand firm)
                4. What is the recommended resolution?
                
                Consider:
                - Accuracy of charge calculations
                - Industry standards
                - Customer relationship value
                - Supporting documentation
                - AI confidence scores
                
                Provide clear, actionable recommendations."""),
                HumanMessage(content=f"Analyze this dispute: {dispute_context}")
            ])
            
            # Get AI analysis
            response = await self.llm.ainvoke(prompt.format_messages())
            
            analysis = {
                "invoice_number": invoice.invoice_number,
                "analysis": response.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Analyzed dispute for invoice {invoice.invoice_number}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing dispute: {e}")
            return {"error": str(e)}
    
    async def draft_collections_email(
        self,
        invoice: Invoice,
        days_overdue: int
    ) -> Dict[str, Any]:
        """
        Draft collection email for overdue invoice.
        
        Args:
            invoice: Overdue invoice
            days_overdue: Number of days past due
            
        Returns:
            Email draft dictionary
        """
        try:
            customer = invoice.customer
            
            # Determine tone based on days overdue
            if days_overdue <= 7:
                tone = "friendly reminder"
            elif days_overdue <= 30:
                tone = "polite but urgent"
            else:
                tone = "formal and serious"
            
            invoice_info = {
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name,
                "total_amount": float(invoice.total_amount),
                "balance_due": float(invoice.balance_due) if invoice.balance_due else 0,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "days_overdue": days_overdue,
                "payment_terms": invoice.payment_terms,
            }
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=f"""You are a professional accounts receivable specialist.
                Draft a {tone} collections email for an overdue invoice.
                
                Your email should:
                - Be professional and respectful
                - Clearly state the amount owed and due date
                - Include payment options
                - Offer to discuss any issues
                - Set clear expectations for payment
                
                Tone: {tone}
                
                Format as a complete email with subject line."""),
                HumanMessage(content=f"Draft collections email for: {invoice_info}")
            ])
            
            # Get AI response
            response = await self.llm.ainvoke(prompt.format_messages())
            
            draft = {
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name,
                "days_overdue": days_overdue,
                "email_draft": response.content,
                "generated_at": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"Generated collections email for invoice {invoice.invoice_number}, "
                f"{days_overdue} days overdue"
            )
            return draft
            
        except Exception as e:
            logger.error(f"Error drafting collections email: {e}")
            return {"error": str(e)}
    
    async def suggest_resolution(
        self,
        invoice: Invoice,
        customer_complaint: str
    ) -> Dict[str, Any]:
        """
        Suggest resolution for customer complaint.
        
        Args:
            invoice: Related invoice
            customer_complaint: Customer's complaint text
            
        Returns:
            Resolution suggestion dictionary
        """
        try:
            customer = invoice.customer
            
            context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name,
                "invoice_amount": float(invoice.total_amount),
                "complaint": customer_complaint,
                "charges": [
                    {
                        "type": c.charge_type.value,
                        "amount": float(c.amount),
                        "description": c.description,
                    }
                    for c in invoice.charges
                ],
            }
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are a customer service manager and conflict resolution expert.
                Based on the customer complaint, suggest the best resolution approach.
                
                Consider:
                - Customer satisfaction vs company revenue
                - Long-term customer value
                - Validity of complaint
                - Industry best practices
                - Fair compromise options
                
                Suggest specific actions:
                - Write off amount (if any)
                - Credit to apply
                - Revised invoice
                - Process improvements
                
                Be specific and actionable."""),
                HumanMessage(content=f"Suggest resolution for: {context}")
            ])
            
            # Get AI suggestion
            response = await self.llm.ainvoke(prompt.format_messages())
            
            suggestion = {
                "invoice_number": invoice.invoice_number,
                "customer_name": customer.name,
                "complaint": customer_complaint,
                "suggested_resolution": response.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"Generated resolution suggestion for invoice {invoice.invoice_number}")
            return suggestion
            
        except Exception as e:
            logger.error(f"Error suggesting resolution: {e}")
            return {"error": str(e)}

