"""Terminal49 Container Tracking API client."""
import hashlib
import hmac
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

import httpx
from pydantic import BaseModel

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ContainerMilestone(BaseModel):
    """Container milestone event."""
    event_type: str
    event_time: datetime
    location: Optional[str] = None
    vessel: Optional[str] = None
    voyage: Optional[str] = None
    description: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class Terminal49Container(BaseModel):
    """Container tracking data from Terminal49."""
    tracking_id: str
    container_number: str
    shipping_line: Optional[str] = None
    vessel_name: Optional[str] = None
    voyage_number: Optional[str] = None
    pol_name: Optional[str] = None
    pod_name: Optional[str] = None
    destination_terminal: Optional[str] = None
    current_status: Optional[str] = None
    location: Optional[str] = None
    vessel_departed_pol: Optional[datetime] = None
    vessel_arrived_pod: Optional[datetime] = None
    vessel_discharged: Optional[datetime] = None
    available_for_pickup: Optional[datetime] = None
    picked_up: Optional[datetime] = None
    delivered: Optional[datetime] = None
    returned_empty: Optional[datetime] = None
    holds: Optional[List[Dict[str, Any]]] = None
    milestones: Optional[List[ContainerMilestone]] = None
    raw_data: Optional[Dict[str, Any]] = None


class Terminal49Client:
    """Client for Terminal49 Container Tracking API."""
    
    API_BASE_URL = "https://api.terminal49.com/v2"
    
    def __init__(self):
        """Initialize Terminal49 client."""
        self.api_key = settings.terminal49_api_key
        self.webhook_secret = settings.terminal49_webhook_secret
        self.timeout = 30.0
        
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def track_container(
        self,
        container_number: str,
        shipping_line: Optional[str] = None,
        ref_numbers: Optional[List[str]] = None
    ) -> Optional[Terminal49Container]:
        """
        Start tracking a container.
        
        Args:
            container_number: Container number to track
            shipping_line: Optional shipping line code (MAEU, CMDU, etc.)
            ref_numbers: Optional reference numbers (booking, BOL, etc.)
            
        Returns:
            Terminal49Container object or None
        """
        try:
            payload = {
                "container_number": container_number.upper().replace(" ", ""),
            }
            
            if shipping_line:
                payload["shipping_line"] = shipping_line.upper()
            
            if ref_numbers:
                payload["ref_numbers"] = ref_numbers
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/trackings",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                container = self._parse_container(data)
                
                logger.info(f"Started tracking container {container_number}")
                return container
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error tracking container {container_number}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error tracking container {container_number}: {e}")
            raise
    
    async def get_container_status(
        self,
        tracking_id: str
    ) -> Optional[Terminal49Container]:
        """
        Get current status of tracked container.
        
        Args:
            tracking_id: Terminal49 tracking ID
            
        Returns:
            Terminal49Container object or None
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/trackings/{tracking_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                
                data = response.json()
                return self._parse_container(data)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Tracking not found: {tracking_id}")
                return None
            logger.error(f"HTTP error fetching tracking {tracking_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching tracking {tracking_id}: {e}")
            raise
    
    async def list_trackings(
        self,
        page: int = 1,
        per_page: int = 50
    ) -> List[Terminal49Container]:
        """
        List all tracked containers.
        
        Args:
            page: Page number
            per_page: Results per page
            
        Returns:
            List of Terminal49Container objects
        """
        try:
            params = {
                "page": page,
                "per_page": per_page,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/trackings",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                
                data = response.json()
                containers = []
                
                for item in data.get("data", []):
                    try:
                        container = self._parse_container(item)
                        containers.append(container)
                    except Exception as e:
                        logger.error(f"Error parsing container: {e}")
                        continue
                
                logger.info(f"Retrieved {len(containers)} tracked containers")
                return containers
                
        except Exception as e:
            logger.error(f"Error listing trackings: {e}")
            raise
    
    async def create_webhook(
        self,
        webhook_url: str,
        events: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a webhook subscription.
        
        Args:
            webhook_url: URL to receive webhooks
            events: List of events to subscribe to (default: all)
            
        Returns:
            Webhook configuration
        """
        try:
            if events is None:
                events = [
                    "container.transport.vessel_discharged",
                    "container.transport.rail_loaded",
                    "container.transport.available_for_pickup",
                    "container.transport.picked_up",
                    "container.transport.delivered",
                    "container.transport.returned_empty",
                    "shipment.updated",
                ]
            
            payload = {
                "url": webhook_url,
                "events": events,
                "active": True,
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.API_BASE_URL}/webhooks",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Created webhook: {data.get('id')}")
                return data
                
        except Exception as e:
            logger.error(f"Error creating webhook: {e}")
            raise
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify webhook signature from Terminal49.
        
        Args:
            payload: Raw webhook payload bytes
            signature: Signature from X-Terminal49-Signature header
            
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def _parse_container(self, data: Dict[str, Any]) -> Terminal49Container:
        """
        Parse raw Terminal49 data into Terminal49Container model.
        
        Args:
            data: Raw API response data
            
        Returns:
            Terminal49Container object
        """
        # Extract container attributes
        attributes = data.get("attributes", {})
        
        # Parse milestones
        milestones = []
        for event in attributes.get("milestones", []):
            try:
                milestone = ContainerMilestone(
                    event_type=event.get("event"),
                    event_time=datetime.fromisoformat(
                        event.get("actual_time", event.get("estimated_time")).replace("Z", "+00:00")
                    ),
                    location=event.get("location"),
                    vessel=event.get("vessel"),
                    voyage=event.get("voyage"),
                    description=event.get("description"),
                    raw_data=event,
                )
                milestones.append(milestone)
            except Exception as e:
                logger.warning(f"Error parsing milestone: {e}")
                continue
        
        # Parse key dates
        vessel_departed_pol = self._parse_date(
            attributes.get("pod_vessel_departed_at")
        )
        vessel_arrived_pod = self._parse_date(
            attributes.get("pod_vessel_arrived_at")
        )
        vessel_discharged = self._parse_date(
            attributes.get("pod_discharged_at")
        )
        available_for_pickup = self._parse_date(
            attributes.get("available_for_pickup_at")
        )
        picked_up = self._parse_date(
            attributes.get("picked_up_at")
        )
        delivered = self._parse_date(
            attributes.get("delivered_at")
        )
        returned_empty = self._parse_date(
            attributes.get("returned_empty_at")
        )
        
        return Terminal49Container(
            tracking_id=data.get("id"),
            container_number=attributes.get("container_number"),
            shipping_line=attributes.get("shipping_line"),
            vessel_name=attributes.get("vessel_name"),
            voyage_number=attributes.get("voyage_number"),
            pol_name=attributes.get("pol_name"),
            pod_name=attributes.get("pod_name"),
            destination_terminal=attributes.get("destination_terminal"),
            current_status=attributes.get("status"),
            location=attributes.get("location"),
            vessel_departed_pol=vessel_departed_pol,
            vessel_arrived_pod=vessel_arrived_pod,
            vessel_discharged=vessel_discharged,
            available_for_pickup=available_for_pickup,
            picked_up=picked_up,
            delivered=delivered,
            returned_empty=returned_empty,
            holds=attributes.get("holds", []),
            milestones=milestones,
            raw_data=data,
        )
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None
    
    async def test_connection(self) -> bool:
        """
        Test connection to Terminal49 API.
        
        Returns:
            True if connection successful
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.API_BASE_URL}/trackings?per_page=1",
                    headers=self.headers,
                )
                response.raise_for_status()
                logger.info("Terminal49 API connection successful")
                return True
        except Exception as e:
            logger.error(f"Terminal49 API connection failed: {e}")
            return False

