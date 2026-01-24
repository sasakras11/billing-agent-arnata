"""McLeod LoadMaster API client."""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

import httpx
from pydantic import BaseModel

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class McLeodLoad(BaseModel):
    """McLeod load data model."""

    customer_name: str
    container_number: Optional[str] = None
    booking_number: Optional[str] = None
    bill_of_lading: Optional[str] = None
    shipper_name: Optional[str] = None
    consignee_name: Optional[str] = None
    pickup_location: Optional[str] = None
    pickup_terminal: Optional[str] = None
    delivery_location: Optional[str] = None
    pickup_date: Optional[datetime] = None
    scheduled_delivery_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    base_freight_rate: Optional[float] = None
    equipment_type: Optional[str] = None
    cargo_weight: Optional[float] = None
    status: str = "pending"
    notes: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class McLeodClient:
    """Client for McLeod LoadMaster REST API."""
    
    def __init__(self):
        """Initialize McLeod client."""
        self.base_url = settings.mcleod_api_url
        self.api_token = settings.mcleod_api_token
        self.company_id = settings.mcleod_company_id
        self.timeout = 30.0
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "X-Company-Id": self.company_id,
        }
    
    async def get_recent_loads(
        self,
        minutes: int = 15,
        load_type: str = "drayage"
    ) -> List[McLeodLoad]:
        """
        Get recent loads from McLeod.
        
        Args:
            minutes: Look back this many minutes
            load_type: Filter by load type (e.g., 'drayage')
            
        Returns:
            List of McLeodLoad objects
        """
        try:
            since = datetime.utcnow() - timedelta(minutes=minutes)
            
            params = {
                "created_after": since.isoformat(),
                "load_type": load_type,
                "include_container": "true",
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/loads",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                
                data = response.json()
                loads = []
                
                for item in data.get("loads", []):
                    try:
                        load = self._parse_load(item)
                        loads.append(load)
                    except Exception as e:
                        logger.error(f"Error parsing load {item.get('order_id')}: {e}")
                        continue
                
                logger.info(f"Retrieved {len(loads)} loads from McLeod")
                return loads
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching loads from McLeod: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching loads from McLeod: {e}")
            raise
    
    async def get_load_by_id(self, order_id: str) -> Optional[McLeodLoad]:
        """
        Get specific load by order ID.
        
        Args:
            order_id: McLeod order ID
            
        Returns:
            McLeodLoad object or None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/loads/{order_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                
                data = response.json()
                return self._parse_load(data)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Load not found: {order_id}")
                return None
            logger.error(f"HTTP error fetching load {order_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching load {order_id}: {e}")
            raise
    
    async def update_load_status(
        self,
        order_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update load status in McLeod.
        
        Args:
            order_id: McLeod order ID
            status: New status
            notes: Optional notes
            
        Returns:
            True if successful
        """
        try:
            payload = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            if notes:
                payload["notes"] = notes
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(
                    f"{self.base_url}/api/v1/loads/{order_id}",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                
                logger.info(f"Updated load {order_id} status to {status}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating load {order_id}: {e}")
            return False
    
    async def get_customer_info(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Get customer information from McLeod.
        
        Args:
            customer_id: McLeod customer ID
            
        Returns:
            Customer data dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/customers/{customer_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                
                return response.json()
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Customer not found: {customer_id}")
                return None
            logger.error(f"HTTP error fetching customer {customer_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching customer {customer_id}: {e}")
            raise
    
    def _parse_load(self, data: Dict[str, Any]) -> McLeodLoad:
        """
        Parse raw McLeod load data into McLeodLoad model.
        
        Args:
            data: Raw API response data
            
        Returns:
            McLeodLoad object
        """
        # Parse dates
        pickup_date = None
        if data.get("pickup_date"):
            try:
                pickup_date = datetime.fromisoformat(data["pickup_date"].replace("Z", "+00:00"))
            except:
                pass
        
        scheduled_delivery_date = None
        if data.get("scheduled_delivery_date"):
            try:
                scheduled_delivery_date = datetime.fromisoformat(
                    data["scheduled_delivery_date"].replace("Z", "+00:00")
                )
            except:
                pass
        
        actual_delivery_date = None
        if data.get("actual_delivery_date"):
            try:
                actual_delivery_date = datetime.fromisoformat(
                    data["actual_delivery_date"].replace("Z", "+00:00")
                )
            except:
                pass
        
        return McLeodLoad(
            order_id=data["order_id"],
            load_number=data.get("load_number", data["order_id"]),
            customer_id=data["customer_id"],
            customer_name=data.get("customer_name", ""),
            container_number=data.get("container_number"),
            booking_number=data.get("booking_number"),
            bill_of_lading=data.get("bill_of_lading"),
            shipper_name=data.get("shipper_name"),
            consignee_name=data.get("consignee_name"),
            pickup_location=data.get("pickup_location"),
            pickup_terminal=data.get("pickup_terminal"),
            delivery_location=data.get("delivery_location"),
            pickup_date=pickup_date,
            scheduled_delivery_date=scheduled_delivery_date,
            actual_delivery_date=actual_delivery_date,
            base_freight_rate=data.get("base_freight_rate"),
            equipment_type=data.get("equipment_type"),
            cargo_weight=data.get("cargo_weight"),
            status=data.get("status", "pending"),
            notes=data.get("notes"),
            raw_data=data,
        )
    
    async def test_connection(self) -> bool:
        """
        Test connection to McLeod API.
        
        Returns:
            True if connection successful
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/health",
                    headers=self.headers,
                )
                response.raise_for_status()
                logger.info("McLeod API connection successful")
                return True
        except Exception as e:
            logger.error(f"McLeod API connection failed: {e}")
            return False

