"""Charge calculation service."""
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from models import Container, Customer, Load, Charge, ChargeType
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ChargeCalculator:
    """Calculate billing charges for containers."""
    
    def __init__(self, db: Session):
        """Initialize calculator with database session."""
        self.db = db
    
    def calculate_last_free_day(
        self,
        container: Container,
        customer: Customer
    ) -> Optional[date]:
        """
        Calculate last free day before charges start.
        
        Args:
            container: Container object
            customer: Customer with rate contract
            
        Returns:
            Last free date or None
        """
        try:
            # Start from vessel discharge or available for pickup
            start_date = None
            
            if container.vessel_discharged:
                start_date = container.vessel_discharged.date()
            elif container.available_for_pickup:
                start_date = container.available_for_pickup.date()
            else:
                logger.warning(f"No start date for container {container.container_number}")
                return None
            
            # Add free days from customer contract
            free_days = customer.free_days or settings.default_free_days
            last_free_day = start_date + timedelta(days=free_days)
            
            logger.info(
                f"Container {container.container_number} last free day: {last_free_day} "
                f"({free_days} free days from {start_date})"
            )
            
            return last_free_day
            
        except Exception as e:
            logger.error(f"Error calculating last free day: {e}")
            return None
    
    def calculate_per_diem(
        self,
        container: Container,
        customer: Customer,
        as_of_date: Optional[date] = None
    ) -> Tuple[int, float]:
        """
        Calculate per diem charges.
        
        Args:
            container: Container object
            customer: Customer with rates
            as_of_date: Calculate as of this date (default: today)
            
        Returns:
            Tuple of (days, amount)
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()
            
            # Container must be picked up but not returned
            if not container.picked_up:
                return (0, 0.0)
            
            if container.returned_empty:
                # Use actual return date
                end_date = container.returned_empty.date()
            else:
                # Calculate up to as_of_date
                end_date = as_of_date
            
            # Calculate from last free day
            if not container.per_diem_starts:
                # Calculate per diem start date
                start_date = container.picked_up.date()
                free_days = customer.per_diem_free_days or customer.free_days or settings.default_free_days
                per_diem_start = start_date + timedelta(days=free_days)
            else:
                per_diem_start = container.per_diem_starts
            
            # Calculate days
            if end_date <= per_diem_start:
                return (0, 0.0)
            
            days = (end_date - per_diem_start).days
            
            # Calculate amount
            rate = customer.per_diem_rate or settings.default_per_diem_rate
            amount = days * rate
            
            logger.info(
                f"Per diem for {container.container_number}: "
                f"{days} days × ${rate} = ${amount}"
            )
            
            return (days, amount)
            
        except Exception as e:
            logger.error(f"Error calculating per diem: {e}")
            return (0, 0.0)
    
    def calculate_demurrage(
        self,
        container: Container,
        customer: Customer,
        as_of_date: Optional[date] = None
    ) -> Tuple[int, float]:
        """
        Calculate demurrage charges (port storage).
        
        Args:
            container: Container object
            customer: Customer with rates
            as_of_date: Calculate as of this date (default: today)
            
        Returns:
            Tuple of (days, amount)
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()
            
            # Container must be discharged but not picked up
            if not container.vessel_discharged:
                return (0, 0.0)
            
            if container.picked_up:
                # Use actual pickup date
                end_date = container.picked_up.date()
            else:
                # Calculate up to as_of_date
                end_date = as_of_date
            
            # Calculate from last free day
            if not container.demurrage_starts:
                start_date = container.vessel_discharged.date()
                free_days = customer.demurrage_free_days or settings.default_free_days
                demurrage_start = start_date + timedelta(days=free_days)
            else:
                demurrage_start = container.demurrage_starts
            
            # Calculate days
            if end_date <= demurrage_start:
                return (0, 0.0)
            
            days = (end_date - demurrage_start).days
            
            # Calculate amount
            rate = customer.demurrage_rate or settings.default_demurrage_rate
            amount = days * rate
            
            logger.info(
                f"Demurrage for {container.container_number}: "
                f"{days} days × ${rate} = ${amount}"
            )
            
            return (days, amount)
            
        except Exception as e:
            logger.error(f"Error calculating demurrage: {e}")
            return (0, 0.0)
    
    def calculate_detention(
        self,
        container: Container,
        customer: Customer,
        as_of_date: Optional[date] = None
    ) -> Tuple[int, float]:
        """
        Calculate detention charges (customer delay).
        
        Args:
            container: Container object
            customer: Customer with rates
            as_of_date: Calculate as of this date (default: today)
            
        Returns:
            Tuple of (days, amount)
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()
            
            # Container must be picked up but not delivered
            if not container.picked_up:
                return (0, 0.0)
            
            if container.delivered:
                # Use actual delivery date
                end_date = container.delivered.date()
            else:
                # Calculate up to as_of_date
                end_date = as_of_date
            
            # Detention typically has 24-48 hour free time
            start_date = container.picked_up.date()
            # Assuming 1 day free time for delivery
            detention_start = start_date + timedelta(days=1)
            
            # Calculate days
            if end_date <= detention_start:
                return (0, 0.0)
            
            days = (end_date - detention_start).days
            
            # Calculate amount
            rate = customer.detention_rate or settings.default_detention_rate
            amount = days * rate
            
            logger.info(
                f"Detention for {container.container_number}: "
                f"{days} days × ${rate} = ${amount}"
            )
            
            return (days, amount)
            
        except Exception as e:
            logger.error(f"Error calculating detention: {e}")
            return (0, 0.0)
    
    def calculate_all_charges(
        self,
        load: Load,
        as_of_date: Optional[date] = None
    ) -> List[Charge]:
        """
        Calculate all charges for a load.
        
        Args:
            load: Load object with container and customer
            as_of_date: Calculate as of this date (default: today)
            
        Returns:
            List of Charge objects (not yet saved to DB)
        """
        try:
            charges = []
            
            if not load.container:
                logger.warning(f"Load {load.id} has no container")
                return charges
            
            container = load.container
            customer = load.customer
            
            # Base freight charge
            if load.base_freight_rate:
                freight_charge = Charge(
                    load_id=load.id,
                    container_id=container.id,
                    charge_type=ChargeType.BASE_FREIGHT,
                    description=f"Base freight - {load.pickup_location} to {load.delivery_location}",
                    rate=load.base_freight_rate,
                    quantity=1.0,
                    amount=load.base_freight_rate,
                    is_billable=True,
                    billable_to_customer=True,
                    ai_confidence_score=1.0,
                )
                charges.append(freight_charge)
            
            # Per diem charges
            per_diem_days, per_diem_amount = self.calculate_per_diem(
                container, customer, as_of_date
            )
            if per_diem_days > 0:
                per_diem_charge = Charge(
                    load_id=load.id,
                    container_id=container.id,
                    charge_type=ChargeType.PER_DIEM,
                    description=f"Per diem charges - {per_diem_days} days",
                    rate=customer.per_diem_rate or settings.default_per_diem_rate,
                    quantity=per_diem_days,
                    amount=per_diem_amount,
                    start_date=container.per_diem_starts,
                    end_date=as_of_date,
                    is_billable=True,
                    billable_to_customer=True,
                    ai_confidence_score=0.95,
                )
                charges.append(per_diem_charge)
            
            # Demurrage charges
            demurrage_days, demurrage_amount = self.calculate_demurrage(
                container, customer, as_of_date
            )
            if demurrage_days > 0:
                demurrage_charge = Charge(
                    load_id=load.id,
                    container_id=container.id,
                    charge_type=ChargeType.DEMURRAGE,
                    description=f"Demurrage charges - {demurrage_days} days",
                    rate=customer.demurrage_rate or settings.default_demurrage_rate,
                    quantity=demurrage_days,
                    amount=demurrage_amount,
                    start_date=container.demurrage_starts,
                    end_date=as_of_date,
                    is_billable=True,
                    billable_to_customer=True,
                    ai_confidence_score=0.95,
                )
                charges.append(demurrage_charge)
            
            # Detention charges
            detention_days, detention_amount = self.calculate_detention(
                container, customer, as_of_date
            )
            if detention_days > 0:
                detention_charge = Charge(
                    load_id=load.id,
                    container_id=container.id,
                    charge_type=ChargeType.DETENTION,
                    description=f"Detention charges - {detention_days} days",
                    rate=customer.detention_rate or settings.default_detention_rate,
                    quantity=detention_days,
                    amount=detention_amount,
                    start_date=container.picked_up.date() if container.picked_up else None,
                    end_date=as_of_date,
                    is_billable=True,
                    billable_to_customer=True,
                    ai_confidence_score=0.90,
                )
                charges.append(detention_charge)
            
            logger.info(
                f"Calculated {len(charges)} charges for load {load.id}, "
                f"total: ${sum(c.amount for c in charges):.2f}"
            )
            
            return charges
            
        except Exception as e:
            logger.error(f"Error calculating all charges for load {load.id}: {e}")
            return []
    
    def should_alert_per_diem(
        self,
        container: Container,
        customer: Customer,
        hours_threshold: int = 24
    ) -> bool:
        """
        Check if we should send per diem alert.
        
        Args:
            container: Container object
            customer: Customer object
            hours_threshold: Alert this many hours before charge starts
            
        Returns:
            True if alert should be sent
        """
        try:
            if not container.per_diem_starts:
                return False
            
            # Calculate hours until per diem starts
            now = datetime.utcnow()
            per_diem_datetime = datetime.combine(
                container.per_diem_starts,
                datetime.min.time()
            )
            
            hours_until = (per_diem_datetime - now).total_seconds() / 3600
            
            # Alert if within threshold and not yet started
            return 0 < hours_until <= hours_threshold
            
        except Exception as e:
            logger.error(f"Error checking per diem alert: {e}")
            return False

