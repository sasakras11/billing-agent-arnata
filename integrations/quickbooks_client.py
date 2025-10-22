"""QuickBooks Online API client."""
import logging
from datetime import date, datetime
from typing import List, Dict, Optional, Any

import httpx
from pydantic import BaseModel

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class QBCustomer(BaseModel):
    """QuickBooks customer."""
    id: str
    display_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    balance: Optional[float] = None


class QBInvoice(BaseModel):
    """QuickBooks invoice."""
    id: str
    doc_number: str
    customer_id: str
    total_amount: float
    balance: float
    due_date: Optional[date] = None
    status: str
    sync_token: str


class QBLineItem(BaseModel):
    """QuickBooks invoice line item."""
    description: str
    amount: float
    quantity: float = 1.0
    unit_price: Optional[float] = None
    item_ref: Optional[str] = None  # Reference to QuickBooks item/service


class QuickBooksClient:
    """Client for QuickBooks Online API."""
    
    SANDBOX_BASE_URL = "https://sandbox-quickbooks.api.intuit.com/v3"
    PRODUCTION_BASE_URL = "https://quickbooks.api.intuit.com/v3"
    
    def __init__(self):
        """Initialize QuickBooks client."""
        self.client_id = settings.quickbooks_client_id
        self.client_secret = settings.quickbooks_client_secret
        self.realm_id = settings.quickbooks_realm_id
        self.environment = settings.quickbooks_environment
        self.timeout = 30.0
        
        # Use sandbox or production URL
        if self.environment == "sandbox":
            self.base_url = f"{self.SANDBOX_BASE_URL}/company/{self.realm_id}"
        else:
            self.base_url = f"{self.PRODUCTION_BASE_URL}/company/{self.realm_id}"
        
        # Access token should be obtained via OAuth2 flow
        # For production, implement proper OAuth2 with token refresh
        self._access_token: Optional[str] = None
    
    def set_access_token(self, access_token: str):
        """Set OAuth2 access token."""
        self._access_token = access_token
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers."""
        if not self._access_token:
            raise ValueError("Access token not set. Call set_access_token() first.")
        
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
    
    async def create_customer(
        self,
        display_name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        payment_terms: str = "Net 30"
    ) -> Optional[QBCustomer]:
        """
        Create customer in QuickBooks.
        
        Args:
            display_name: Customer display name
            email: Customer email
            phone: Customer phone
            payment_terms: Payment terms (default: Net 30)
            
        Returns:
            QBCustomer object or None
        """
        try:
            payload = {
                "DisplayName": display_name,
                "SalesTermRef": {"value": payment_terms},
            }
            
            if email:
                payload["PrimaryEmailAddr"] = {"Address": email}
            
            if phone:
                payload["PrimaryPhone"] = {"FreeFormNumber": phone}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/customer",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                customer_data = data.get("Customer", {})
                
                customer = QBCustomer(
                    id=customer_data["Id"],
                    display_name=customer_data["DisplayName"],
                    email=customer_data.get("PrimaryEmailAddr", {}).get("Address"),
                    phone=customer_data.get("PrimaryPhone", {}).get("FreeFormNumber"),
                    balance=customer_data.get("Balance", 0.0),
                )
                
                logger.info(f"Created QuickBooks customer: {customer.display_name}")
                return customer
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating customer: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating customer: {e}")
            raise
    
    async def get_customer(self, customer_id: str) -> Optional[QBCustomer]:
        """
        Get customer by ID.
        
        Args:
            customer_id: QuickBooks customer ID
            
        Returns:
            QBCustomer object or None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/customer/{customer_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                
                data = response.json()
                customer_data = data.get("Customer", {})
                
                return QBCustomer(
                    id=customer_data["Id"],
                    display_name=customer_data["DisplayName"],
                    email=customer_data.get("PrimaryEmailAddr", {}).get("Address"),
                    phone=customer_data.get("PrimaryPhone", {}).get("FreeFormNumber"),
                    balance=customer_data.get("Balance", 0.0),
                )
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Customer not found: {customer_id}")
                return None
            raise
        except Exception as e:
            logger.error(f"Error fetching customer {customer_id}: {e}")
            raise
    
    async def create_invoice(
        self,
        customer_id: str,
        line_items: List[QBLineItem],
        invoice_date: Optional[date] = None,
        due_date: Optional[date] = None,
        doc_number: Optional[str] = None,
        memo: Optional[str] = None
    ) -> Optional[QBInvoice]:
        """
        Create invoice in QuickBooks.
        
        Args:
            customer_id: QuickBooks customer ID
            line_items: List of line items
            invoice_date: Invoice date (default: today)
            due_date: Due date
            doc_number: Invoice number (auto-generated if not provided)
            memo: Invoice memo/notes
            
        Returns:
            QBInvoice object or None
        """
        try:
            if invoice_date is None:
                invoice_date = date.today()
            
            # Build line items
            lines = []
            for idx, item in enumerate(line_items, 1):
                line = {
                    "DetailType": "SalesItemLineDetail",
                    "Amount": item.amount,
                    "Description": item.description,
                    "SalesItemLineDetail": {
                        "Qty": item.quantity,
                        "UnitPrice": item.unit_price or (item.amount / item.quantity),
                    }
                }
                
                # Add item reference if provided
                if item.item_ref:
                    line["SalesItemLineDetail"]["ItemRef"] = {"value": item.item_ref}
                
                lines.append(line)
            
            payload = {
                "CustomerRef": {"value": customer_id},
                "TxnDate": invoice_date.isoformat(),
                "Line": lines,
            }
            
            if due_date:
                payload["DueDate"] = due_date.isoformat()
            
            if doc_number:
                payload["DocNumber"] = doc_number
            
            if memo:
                payload["CustomerMemo"] = {"value": memo}
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/invoice",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                invoice_data = data.get("Invoice", {})
                
                invoice = QBInvoice(
                    id=invoice_data["Id"],
                    doc_number=invoice_data["DocNumber"],
                    customer_id=invoice_data["CustomerRef"]["value"],
                    total_amount=float(invoice_data["TotalAmt"]),
                    balance=float(invoice_data["Balance"]),
                    due_date=datetime.strptime(
                        invoice_data["DueDate"], "%Y-%m-%d"
                    ).date() if invoice_data.get("DueDate") else None,
                    status="Open" if float(invoice_data["Balance"]) > 0 else "Paid",
                    sync_token=invoice_data["SyncToken"],
                )
                
                logger.info(f"Created invoice {invoice.doc_number} for customer {customer_id}")
                return invoice
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error creating invoice: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise
    
    async def get_invoice(self, invoice_id: str) -> Optional[QBInvoice]:
        """
        Get invoice by ID.
        
        Args:
            invoice_id: QuickBooks invoice ID
            
        Returns:
            QBInvoice object or None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/invoice/{invoice_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                
                data = response.json()
                invoice_data = data.get("Invoice", {})
                
                return QBInvoice(
                    id=invoice_data["Id"],
                    doc_number=invoice_data["DocNumber"],
                    customer_id=invoice_data["CustomerRef"]["value"],
                    total_amount=float(invoice_data["TotalAmt"]),
                    balance=float(invoice_data["Balance"]),
                    due_date=datetime.strptime(
                        invoice_data["DueDate"], "%Y-%m-%d"
                    ).date() if invoice_data.get("DueDate") else None,
                    status="Open" if float(invoice_data["Balance"]) > 0 else "Paid",
                    sync_token=invoice_data["SyncToken"],
                )
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Invoice not found: {invoice_id}")
                return None
            raise
        except Exception as e:
            logger.error(f"Error fetching invoice {invoice_id}: {e}")
            raise
    
    async def send_invoice(
        self,
        invoice_id: str,
        email_address: Optional[str] = None
    ) -> bool:
        """
        Send invoice to customer via email.
        
        Args:
            invoice_id: QuickBooks invoice ID
            email_address: Optional email address (uses customer email if not provided)
            
        Returns:
            True if successful
        """
        try:
            params = {}
            if email_address:
                params["sendTo"] = email_address
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/invoice/{invoice_id}/send",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                
                logger.info(f"Sent invoice {invoice_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error sending invoice {invoice_id}: {e}")
            return False
    
    async def query_invoices(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[QBInvoice]:
        """
        Query invoices with filters.
        
        Args:
            customer_id: Filter by customer ID
            status: Filter by status (Open, Paid, etc.)
            
        Returns:
            List of QBInvoice objects
        """
        try:
            # Build query
            conditions = []
            if customer_id:
                conditions.append(f"CustomerRef = '{customer_id}'")
            if status:
                conditions.append(f"Balance {'>' if status == 'Open' else '='} 0")
            
            where_clause = " AND ".join(conditions) if conditions else ""
            query = f"SELECT * FROM Invoice"
            if where_clause:
                query += f" WHERE {where_clause}"
            query += " MAXRESULTS 100"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/query",
                    headers=self.headers,
                    params={"query": query},
                )
                response.raise_for_status()
                
                data = response.json()
                invoices = []
                
                for invoice_data in data.get("QueryResponse", {}).get("Invoice", []):
                    try:
                        invoice = QBInvoice(
                            id=invoice_data["Id"],
                            doc_number=invoice_data["DocNumber"],
                            customer_id=invoice_data["CustomerRef"]["value"],
                            total_amount=float(invoice_data["TotalAmt"]),
                            balance=float(invoice_data["Balance"]),
                            due_date=datetime.strptime(
                                invoice_data["DueDate"], "%Y-%m-%d"
                            ).date() if invoice_data.get("DueDate") else None,
                            status="Open" if float(invoice_data["Balance"]) > 0 else "Paid",
                            sync_token=invoice_data["SyncToken"],
                        )
                        invoices.append(invoice)
                    except Exception as e:
                        logger.error(f"Error parsing invoice: {e}")
                        continue
                
                return invoices
                
        except Exception as e:
            logger.error(f"Error querying invoices: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """
        Test connection to QuickBooks API.
        
        Returns:
            True if connection successful
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/companyinfo/{self.realm_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                logger.info("QuickBooks API connection successful")
                return True
        except Exception as e:
            logger.error(f"QuickBooks API connection failed: {e}")
            return False

