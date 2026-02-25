"""AI Agent for handling billing disputes."""
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List
from enum import Enum

from sqlalchemy.orm import Session

from models import Invoice, Customer
from config import get_settings
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)
settings = get_settings()


class DisputeCategory(str, Enum):
    """Categories of dispute types."""
    PRICING_ERROR = "pricing_error"
    SERVICE_NOT_RENDERED = "service_not_rendered"
    QUALITY_ISSUE = "quality_issue"
    DUPLICATE_CHARGE = "duplicate_charge"
    ALREADY_PAID = "already_paid"
    CONTRACTUAL_DISAGREEMENT = "contractual_disagreement"
    OTHER = "other"


class DisputeSentiment(str, Enum):
    """Sentiment analysis of customer dispute."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    THREATENING = "threatening"


def _charge_summary(invoice: Invoice) -> list[dict]:
    """Build a compact charge list from an invoice."""
    return [
        {
            "type": c.charge_type.value,
            "description": c.description,
            "amount": float(c.amount),
            "quantity": float(c.quantity),
            "rate": float(c.rate),
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
        }
        for c in invoice.charges
    ]


def _charge_brief(invoice: Invoice) -> list[dict]:
    """Build a brief charge list (type, amount, description) from an invoice."""
    return [
        {"type": c.charge_type.value, "amount": float(c.amount), "description": c.description}
        for c in invoice.charges
    ]


class DisputeAgent(BaseAgent):
    """AI Agent for handling payment disputes and customer communications."""

    def __init__(self, db: Session):
        super().__init__(db, temperature=settings.llm_temperature_creative)

    async def draft_dispute_response(
        self,
        invoice: Invoice,
        dispute_reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Draft professional email response to disputed invoice."""
        try:
            context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "invoice_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0,
                "dispute_amount": float(invoice.dispute_amount) if invoice.dispute_amount else 0,
                "charges": _charge_summary(invoice),
                "dispute_reason": dispute_reason or "Not specified",
            }
            content = await self._invoke_llm(
                system_message="""You are a professional customer service representative for a trucking company.
                Draft a polite, professional email response to a customer who disputed an invoice.
                Your email should clearly explain each charge, reference specific dates and rates,
                offer documentation, and maintain a firm but courteous tone.
                Format: Subject line, greeting, structured body, professional closing.""",
                human_message=f"Customer disputed invoice details:\n{context}\n\nPlease draft a response email.",
                log_message=f"Generated dispute response for invoice {invoice.invoice_number}",
            )
            return {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "email_draft": content,
                "generated_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error drafting dispute response: {e}")
            return {"error": str(e)}

    async def analyze_dispute(self, invoice: Invoice) -> Dict[str, Any]:
        """Analyze dispute validity and recommend action."""
        try:
            context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "invoice_amount": float(invoice.total_amount),
                "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0,
                "dispute_amount": float(invoice.dispute_amount) if invoice.dispute_amount else 0,
                "dispute_reason": invoice.dispute_reason,
                "charges": [
                    {**b, "is_disputed": c.is_disputed,
                     "confidence": float(c.ai_confidence_score) if c.ai_confidence_score else 0}
                    for b, c in zip(_charge_brief(invoice), invoice.charges)
                ],
            }
            content = await self._invoke_llm(
                system_message="""You are a billing dispute analyst for a trucking company.
                Determine if the dispute is valid, which charges are questionable,
                and recommend action (write off, negotiate, or stand firm).
                Consider charge accuracy, industry standards, customer value, and AI confidence scores.""",
                human_message=f"Analyze this dispute: {context}",
                log_message=f"Analyzed dispute for invoice {invoice.invoice_number}",
            )
            return {
                "invoice_number": invoice.invoice_number,
                "analysis": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error analyzing dispute: {e}")
            return {"error": str(e)}

    async def draft_collections_email(
        self,
        invoice: Invoice,
        days_overdue: int,
    ) -> Dict[str, Any]:
        """Draft collection email for overdue invoice."""
        try:
            if days_overdue <= 7:
                tone = "friendly reminder"
            elif days_overdue <= 30:
                tone = "polite but urgent"
            else:
                tone = "formal and serious"

            context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "total_amount": float(invoice.total_amount),
                "balance_due": float(invoice.balance_due) if invoice.balance_due else 0,
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "days_overdue": days_overdue,
                "payment_terms": invoice.payment_terms,
            }
            content = await self._invoke_llm(
                system_message=f"""You are a professional accounts receivable specialist.
                Draft a {tone} collections email. Be professional, state the amount owed,
                include payment options, and set clear expectations. Tone: {tone}.
                Format as a complete email with subject line.""",
                human_message=f"Draft collections email for: {context}",
                log_message=(
                    f"Generated collections email for invoice {invoice.invoice_number}, "
                    f"{days_overdue} days overdue"
                ),
            )
            return {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "days_overdue": days_overdue,
                "email_draft": content,
                "generated_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error drafting collections email: {e}")
            return {"error": str(e)}

    async def suggest_resolution(
        self,
        invoice: Invoice,
        customer_complaint: str,
    ) -> Dict[str, Any]:
        """Suggest resolution for customer complaint."""
        try:
            context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "invoice_amount": float(invoice.total_amount),
                "complaint": customer_complaint,
                "charges": _charge_brief(invoice),
            }
            content = await self._invoke_llm(
                system_message="""You are a customer service manager and conflict resolution expert.
                Suggest the best resolution: write-off amount, credit to apply, revised invoice,
                or process improvements. Balance customer satisfaction with company revenue.
                Be specific and actionable.""",
                human_message=f"Suggest resolution for: {context}",
                log_message=f"Generated resolution suggestion for invoice {invoice.invoice_number}",
            )
            return {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "complaint": customer_complaint,
                "suggested_resolution": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error suggesting resolution: {e}")
            return {"error": str(e)}

    async def analyze_dispute_sentiment(self, customer_message: str) -> Dict[str, Any]:
        """Analyze sentiment and urgency of customer dispute message."""
        try:
            content = await self._invoke_llm(
                system_message="""You are a sentiment analysis expert.
                Determine sentiment (positive/neutral/frustrated/angry/threatening),
                urgency (low/medium/high/critical), key concerns, and tone indicators.
                Return JSON: {"sentiment","urgency","key_concerns","tone_indicators","recommended_response_time"}""",
                human_message=f"Analyze this customer message:\n\n{customer_message}",
                log_message="Analyzed customer dispute sentiment",
            )
            return {
                "customer_message": customer_message,
                "sentiment_analysis": content,
                "analyzed_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"error": str(e)}

    async def categorize_dispute(
        self,
        dispute_description: str,
        invoice: Optional[Invoice] = None,
    ) -> Dict[str, Any]:
        """Categorize the type of dispute."""
        try:
            context: Dict[str, Any] = {"dispute_description": dispute_description}
            if invoice:
                context["invoice_amount"] = float(invoice.total_amount)
                context["charges"] = _charge_brief(invoice)

            categories_list = [cat.value for cat in DisputeCategory]
            content = await self._invoke_llm(
                system_message=f"""You are a billing dispute categorization expert.
                Categorize into one of: {', '.join(categories_list)}.
                Provide primary category, confidence (0-1), secondary categories, and reasoning.""",
                human_message=f"Categorize this dispute:\n\n{context}",
                log_message="Categorized dispute",
            )
            return {
                "dispute_description": dispute_description,
                "categorization": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error categorizing dispute: {e}")
            return {"error": str(e)}

    async def generate_dispute_summary(
        self,
        invoice: Invoice,
        customer_messages: List[str],
    ) -> Dict[str, Any]:
        """Generate executive summary of dispute conversation."""
        try:
            context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "invoice_amount": float(invoice.total_amount),
                "messages": customer_messages,
            }
            content = await self._invoke_llm(
                system_message="""You are an executive assistant summarizing dispute cases.
                Create a concise summary (<200 words) covering: key facts, customer concerns,
                current status, recommended actions, and risk level (low/medium/high).""",
                human_message=f"Summarize this dispute case:\n\n{context}",
                log_message=f"Generated dispute summary for invoice {invoice.invoice_number}",
            )
            return {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "executive_summary": content,
                "messages_reviewed": len(customer_messages),
                "generated_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error generating dispute summary: {e}")
            return {"error": str(e)}

    async def calculate_goodwill_credit(
        self,
        invoice: Invoice,
        customer_complaint: str,
        customer_lifetime_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calculate recommended goodwill credit amount."""
        try:
            context = {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "invoice_amount": float(invoice.total_amount),
                "complaint": customer_complaint,
                "customer_lifetime_value": customer_lifetime_value,
            }
            content = await self._invoke_llm(
                system_message="""You are a customer retention specialist.
                Recommend a goodwill credit: specific dollar amount or percentage, justification,
                how to present it, and any additional gestures. Balance satisfaction with profitability.""",
                human_message=f"Calculate goodwill credit for:\n\n{context}",
                log_message=(
                    f"Calculated goodwill credit recommendation for invoice {invoice.invoice_number}"
                ),
            )
            return {
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer.name,
                "goodwill_recommendation": content,
                "calculated_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error(f"Error calculating goodwill credit: {e}")
            return {"error": str(e)}
