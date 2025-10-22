"""AI Agent for container tracking automation."""
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from models import Container, Load, Customer, ContainerEvent
from integrations.terminal49_client import Terminal49Client
from services.alert_service import AlertService
from services.charge_calculator import ChargeCalculator
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TrackingAgent:
    """AI Agent for monitoring and tracking containers."""
    
    def __init__(self, db: Session):
        """
        Initialize tracking agent.
        
        Args:
            db: Database session
        """
        self.db = db
        self.terminal49 = Terminal49Client()
        self.alert_service = AlertService(db)
        self.charge_calculator = ChargeCalculator(db)
        
        # Initialize Claude LLM
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-20241022",
            anthropic_api_key=settings.anthropic_api_key,
            temperature=0.3,
        )
    
    async def start_tracking_container(
        self,
        container_number: str,
        load: Load
    ) -> Optional[Container]:
        """
        Start tracking a container.
        
        Args:
            container_number: Container number to track
            load: Associated load
            
        Returns:
            Container object or None
        """
        try:
            # Check if already tracking
            existing = (
                self.db.query(Container)
                .filter(Container.container_number == container_number)
                .first()
            )
            
            if existing:
                logger.info(f"Already tracking container {container_number}")
                return existing
            
            # Start tracking via Terminal49
            t49_container = await self.terminal49.track_container(
                container_number=container_number,
                ref_numbers=[load.bill_of_lading] if load.bill_of_lading else None
            )
            
            if not t49_container:
                logger.error(f"Failed to track container {container_number}")
                return None
            
            # Create container record
            container = Container(
                container_number=container_number,
                load_id=load.id,
                terminal49_tracking_id=t49_container.tracking_id,
                shipping_line=t49_container.shipping_line,
                vessel_name=t49_container.vessel_name,
                voyage_number=t49_container.voyage_number,
                pol_name=t49_container.pol_name,
                pod_name=t49_container.pod_name,
                destination_terminal=t49_container.destination_terminal,
                current_status=t49_container.current_status,
                location=t49_container.location,
                vessel_departed_pol=t49_container.vessel_departed_pol,
                vessel_arrived_pod=t49_container.vessel_arrived_pod,
                vessel_discharged=t49_container.vessel_discharged,
                available_for_pickup=t49_container.available_for_pickup,
                picked_up=t49_container.picked_up,
                delivered=t49_container.delivered,
                returned_empty=t49_container.returned_empty,
                holds=t49_container.holds,
                is_tracking_active=True,
                raw_terminal49_data=t49_container.raw_data,
            )
            
            self.db.add(container)
            
            # Calculate last free day
            customer = load.customer
            last_free_day = self.charge_calculator.calculate_last_free_day(
                container, customer
            )
            if last_free_day:
                container.last_free_day = last_free_day
                container.per_diem_starts = last_free_day
            
            self.db.commit()
            
            # Create milestone events
            if t49_container.milestones:
                for milestone in t49_container.milestones:
                    event = ContainerEvent(
                        container_id=container.id,
                        event_type=milestone.event_type,
                        event_time=milestone.event_time,
                        location=milestone.location,
                        vessel=milestone.vessel,
                        voyage=milestone.voyage,
                        description=milestone.description,
                        raw_data=milestone.raw_data,
                    )
                    self.db.add(event)
                
                self.db.commit()
            
            logger.info(f"Started tracking container {container_number}")
            
            # Send initial alert if container is available
            if container.available_for_pickup:
                self.alert_service.create_container_available_alert(
                    container, customer
                )
            
            return container
            
        except Exception as e:
            logger.error(f"Error starting tracking for {container_number}: {e}")
            self.db.rollback()
            return None
    
    async def update_container_status(
        self,
        container: Container
    ) -> bool:
        """
        Update container status from Terminal49.
        
        Args:
            container: Container object
            
        Returns:
            True if updated successfully
        """
        try:
            if not container.terminal49_tracking_id:
                logger.warning(f"Container {container.id} has no tracking ID")
                return False
            
            # Get latest status from Terminal49
            t49_container = await self.terminal49.get_container_status(
                container.terminal49_tracking_id
            )
            
            if not t49_container:
                logger.error(f"Failed to get status for container {container.id}")
                return False
            
            # Update container fields
            container.current_status = t49_container.current_status
            container.location = t49_container.location
            container.vessel_departed_pol = t49_container.vessel_departed_pol
            container.vessel_arrived_pod = t49_container.vessel_arrived_pod
            container.vessel_discharged = t49_container.vessel_discharged
            container.available_for_pickup = t49_container.available_for_pickup
            container.picked_up = t49_container.picked_up
            container.delivered = t49_container.delivered
            container.returned_empty = t49_container.returned_empty
            container.holds = t49_container.holds
            container.last_updated = datetime.utcnow()
            container.raw_terminal49_data = t49_container.raw_data
            
            self.db.commit()
            
            logger.info(f"Updated container {container.container_number} status: {container.current_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating container {container.id}: {e}")
            self.db.rollback()
            return False
    
    def check_alerts(self, container: Container) -> List[str]:
        """
        Check if alerts should be sent for container.
        
        Args:
            container: Container object
            
        Returns:
            List of alert messages
        """
        try:
            alerts = []
            
            if not container.load or not container.load.customer:
                return alerts
            
            customer = container.load.customer
            
            # Check per diem alert
            if self.charge_calculator.should_alert_per_diem(
                container, customer, hours_threshold=24
            ):
                self.alert_service.create_per_diem_alert(
                    container, customer, hours_until=24
                )
                alerts.append("Per diem alert created")
            
            # Check if charges are accruing
            if container.picked_up and not container.returned_empty:
                per_diem_days, per_diem_amount = self.charge_calculator.calculate_per_diem(
                    container, customer
                )
                if per_diem_days > 0:
                    self.alert_service.create_charge_accruing_alert(
                        container,
                        customer,
                        "per_diem",
                        customer.per_diem_rate or settings.default_per_diem_rate
                    )
                    alerts.append(f"Per diem accruing: {per_diem_days} days")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
            return []
    
    async def analyze_container_risk(
        self,
        container: Container
    ) -> Dict[str, Any]:
        """
        Use AI to analyze container for charge risk.
        
        Args:
            container: Container object
            
        Returns:
            Analysis dictionary
        """
        try:
            # Prepare container data for AI
            container_data = {
                "container_number": container.container_number,
                "current_status": container.current_status,
                "location": container.location,
                "vessel_discharged": container.vessel_discharged.isoformat() if container.vessel_discharged else None,
                "available_for_pickup": container.available_for_pickup.isoformat() if container.available_for_pickup else None,
                "picked_up": container.picked_up.isoformat() if container.picked_up else None,
                "delivered": container.delivered.isoformat() if container.delivered else None,
                "returned_empty": container.returned_empty.isoformat() if container.returned_empty else None,
                "last_free_day": container.last_free_day.isoformat() if container.last_free_day else None,
                "per_diem_days": container.per_diem_days,
                "demurrage_days": container.demurrage_days,
                "holds": container.holds,
            }
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are an expert in intermodal trucking and container logistics. 
                Analyze the container status and provide risk assessment for potential charges (per diem, demurrage, detention).
                Consider:
                - Current location and status
                - Time elapsed since key milestones
                - Any holds or delays
                - Free time remaining
                
                Provide a risk level (low, medium, high, critical) and specific recommendations."""),
                HumanMessage(content=f"Analyze this container: {container_data}")
            ])
            
            # Get AI analysis
            response = await self.llm.ainvoke(prompt.format_messages())
            
            analysis = {
                "container_number": container.container_number,
                "analysis": response.content,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info(f"AI analysis completed for container {container.container_number}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing container risk: {e}")
            return {
                "error": str(e),
                "container_number": container.container_number,
            }
    
    async def should_prepull_container(
        self,
        container: Container,
        customer: Customer
    ) -> Dict[str, Any]:
        """
        AI decision: Should we pre-pull this container?
        
        Args:
            container: Container object
            customer: Customer object
            
        Returns:
            Decision dictionary with reasoning
        """
        try:
            # Calculate potential savings
            days_until_last_free = 0
            if container.last_free_day:
                days_until_last_free = (container.last_free_day - datetime.utcnow().date()).days
            
            potential_per_diem = (
                customer.per_diem_rate or settings.default_per_diem_rate
            ) * max(0, 3)  # Estimate 3 days saved
            
            prepull_cost = customer.pre_pull_fee or 75.0
            
            # Prepare data for AI
            decision_data = {
                "container_number": container.container_number,
                "location": container.location,
                "available_for_pickup": container.available_for_pickup.isoformat() if container.available_for_pickup else None,
                "days_until_last_free": days_until_last_free,
                "prepull_cost": prepull_cost,
                "potential_per_diem_per_day": customer.per_diem_rate or settings.default_per_diem_rate,
                "estimated_savings": potential_per_diem - prepull_cost,
            }
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content="""You are an expert logistics analyst specializing in cost optimization.
                Analyze whether pre-pulling this container makes financial sense.
                Consider:
                - Pre-pull fee vs potential per diem charges
                - Days remaining until charges start
                - Current location and availability
                - Risk of delays
                
                Provide a clear YES or NO decision with detailed reasoning."""),
                HumanMessage(content=f"Should we pre-pull this container? {decision_data}")
            ])
            
            # Get AI decision
            response = await self.llm.ainvoke(prompt.format_messages())
            
            decision = {
                "container_number": container.container_number,
                "recommendation": "YES" if "YES" in response.content.upper()[:50] else "NO",
                "reasoning": response.content,
                "estimated_savings": decision_data["estimated_savings"],
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info(
                f"Pre-pull decision for {container.container_number}: "
                f"{decision['recommendation']}"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error making pre-pull decision: {e}")
            return {
                "error": str(e),
                "container_number": container.container_number,
                "recommendation": "ERROR",
            }

