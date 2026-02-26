"""Charge calculation service."""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from models import Container, Customer, Load, Charge, ChargeType
from config import get_settings
from utils.validation import validate_positive_amount, validate_days

logger = logging.getLogger(__name__)
settings = get_settings()


class ChargeCalculator:
    """Calculate billing charges for containers."""
    
    def __init__(self, db: Session):
        """Initialize calculator with database session."""
        self.db = db
        self._rate_cache = {}  # Cache for customer rates
    
    def calculate_last_free_day(self, container: Container, customer: Customer) -> Optional[date]:
        """Calculate last free day before charges start."""
        try:
            start_date = (container.vessel_discharged or container.available_for_pickup)
            if not start_date:
                logger.warning(f"No start date for container {container.container_number}")
                return None
            
            free_days = customer.free_days or settings.default_free_days
            last_free_day = start_date.date() + timedelta(days=free_days)
            logger.info(f"Container {container.container_number} last free day: {last_free_day} ({free_days} free days)")
            return last_free_day
        except Exception as e:
            logger.error(f"Error calculating last free day: {e}")
            return None
    
    def _get_customer_rate(self, customer: Customer, rate_type: str, default_rate: float) -> float:
        """Get customer rate with caching and validation."""
        cache_key = f"{customer.id}_{rate_type}"
        if cache_key not in self._rate_cache:
            rate = getattr(customer, rate_type, None) or default_rate
            try:
                self._rate_cache[cache_key] = validate_positive_amount(rate, rate_type, allow_zero=False)
            except Exception as e:
                logger.warning(f"Invalid rate for {rate_type}, using default: {e}")
                self._rate_cache[cache_key] = default_rate
        return self._rate_cache[cache_key]
    
    def _calculate_charge_days(
        self,
        start_date: Optional[date],
        end_date: date,
        free_days: int,
        stored_start: Optional[date] = None
    ) -> int:
        """Calculate chargeable days between start and end dates."""
        if not start_date:
            return 0
        charge_start = stored_start or (start_date + timedelta(days=free_days))
        if end_date <= charge_start:
            return 0
        return max(0, (end_date - charge_start).days)

    def _calc(
        self,
        container: Container,
        customer: Customer,
        start_date: Optional[date],
        end_date: date,
        free_days: int,
        rate_field: str,
        default_rate: float,
        stored_start: Optional[date],
        label: str,
    ) -> Tuple[int, float]:
        """Core per-day charge calculation shared by per diem, demurrage, and detention."""
        days = self._calculate_charge_days(
            start_date, end_date, validate_days(free_days, rate_field), stored_start
        )
        if days == 0:
            return (0, 0.0)
        rate = self._get_customer_rate(customer, rate_field, default_rate)
        amount = days * rate
        logger.info(f"{label} for {container.container_number}: {days} days × ${rate} = ${amount}")
        return (days, amount)

    def calculate_per_diem(
        self,
        container: Container,
        customer: Customer,
        as_of_date: Optional[date] = None
    ) -> Tuple[int, float]:
        """Calculate per diem charges."""
        try:
            as_of_date = as_of_date or date.today()
            if not container.picked_up:
                return (0, 0.0)
            return self._calc(
                container, customer,
                start_date=container.picked_up.date(),
                end_date=container.returned_empty.date() if container.returned_empty else as_of_date,
                free_days=customer.per_diem_free_days or customer.free_days or settings.default_free_days,
                rate_field='per_diem_rate',
                default_rate=settings.default_per_diem_rate,
                stored_start=container.per_diem_starts,
                label="Per diem",
            )
        except Exception as e:
            logger.error(f"Error calculating per diem: {e}")
            return (0, 0.0)

    def calculate_demurrage(
        self,
        container: Container,
        customer: Customer,
        as_of_date: Optional[date] = None
    ) -> Tuple[int, float]:
        """Calculate demurrage charges (port storage)."""
        try:
            as_of_date = as_of_date or date.today()
            if not container.vessel_discharged:
                return (0, 0.0)
            return self._calc(
                container, customer,
                start_date=container.vessel_discharged.date(),
                end_date=container.picked_up.date() if container.picked_up else as_of_date,
                free_days=customer.demurrage_free_days or settings.default_free_days,
                rate_field='demurrage_rate',
                default_rate=settings.default_demurrage_rate,
                stored_start=container.demurrage_starts,
                label="Demurrage",
            )
        except Exception as e:
            logger.error(f"Error calculating demurrage: {e}")
            return (0, 0.0)

    def calculate_detention(
        self,
        container: Container,
        customer: Customer,
        as_of_date: Optional[date] = None
    ) -> Tuple[int, float]:
        """Calculate detention charges (customer delay)."""
        try:
            as_of_date = as_of_date or date.today()
            if not container.picked_up:
                return (0, 0.0)
            return self._calc(
                container, customer,
                start_date=container.picked_up.date(),
                end_date=container.delivered.date() if container.delivered else as_of_date,
                free_days=1,
                rate_field='detention_rate',
                default_rate=settings.default_detention_rate,
                stored_start=None,
                label="Detention",
            )
        except Exception as e:
            logger.error(f"Error calculating detention: {e}")
            return (0, 0.0)
    
    def calculate_all_charges(self, load: Load, as_of_date: Optional[date] = None) -> List[Charge]:
        """Calculate all charges for a load (not saved to DB)."""
        try:
            charges = []
            
            if not load.container:
                logger.warning(f"Load {load.id} has no container")
                return charges
            
            container = load.container
            customer = load.customer
            
            if load.base_freight_rate:
                charges.append(Charge(
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
                ))
            
            def _create_charge(charge_type, days, amount, rate, description, start_date, confidence=0.95):
                if days > 0:
                    return Charge(
                        load_id=load.id,
                        container_id=container.id,
                        charge_type=charge_type,
                        description=description,
                        rate=rate,
                        quantity=days,
                        amount=amount,
                        start_date=start_date,
                        end_date=as_of_date,
                        is_billable=True,
                        billable_to_customer=True,
                        ai_confidence_score=confidence,
                    )
                return None

            per_diem_days, per_diem_amount = self.calculate_per_diem(container, customer, as_of_date)
            if charge := _create_charge(
                ChargeType.PER_DIEM, per_diem_days, per_diem_amount,
                customer.per_diem_rate or settings.default_per_diem_rate,
                f"Per diem charges - {per_diem_days} days",
                container.per_diem_starts
            ):
                charges.append(charge)

            demurrage_days, demurrage_amount = self.calculate_demurrage(container, customer, as_of_date)
            if charge := _create_charge(
                ChargeType.DEMURRAGE, demurrage_days, demurrage_amount,
                customer.demurrage_rate or settings.default_demurrage_rate,
                f"Demurrage charges - {demurrage_days} days",
                container.demurrage_starts
            ):
                charges.append(charge)

            detention_days, detention_amount = self.calculate_detention(container, customer, as_of_date)
            if charge := _create_charge(
                ChargeType.DETENTION, detention_days, detention_amount,
                customer.detention_rate or settings.default_detention_rate,
                f"Detention charges - {detention_days} days",
                container.picked_up.date() if container.picked_up else None,
                0.90
            ):
                charges.append(charge)
            
            logger.info(
                f"Calculated {len(charges)} charges for load {load.id}, "
                f"total: ${sum(c.amount for c in charges):.2f}"
            )
            
            return charges
            
        except Exception as e:
            logger.error(f"Error calculating all charges for load {load.id}: {e}")
            return []
    
    def should_alert_per_diem(self, container: Container, customer: Customer, hours_threshold: int = 24) -> bool:
        """Check if we should send per diem alert."""
        try:
            if not container.per_diem_starts:
                return False
            now = datetime.utcnow()
            per_diem_datetime = datetime.combine(container.per_diem_starts, datetime.min.time())
            hours_until = (per_diem_datetime - now).total_seconds() / 3600
            return 0 < hours_until <= hours_threshold
        except Exception as e:
            logger.error(f"Error checking per diem alert: {e}")
            return False

