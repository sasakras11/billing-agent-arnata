"""Repository for load operations."""
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from models import Load, Charge
from repositories.base import BaseRepository
from logging_config import get_logger

logger = get_logger(__name__)


class LoadRepository(BaseRepository[Load]):
    """Repository for load-specific database operations."""

    def __init__(self, db: Session):
        super().__init__(Load, db)

    def get_by_load_number(self, load_number: str) -> Optional[Load]:
        """Get load by load number."""
        return self.db.query(Load).filter(
            Load.mcleod_load_number == load_number
        ).first()

    def get_by_customer(
        self, customer_id: int, skip: int = 0, limit: int = 100
    ) -> List[Load]:
        """Get loads for a customer."""
        return self.db.query(Load).filter(
            Load.customer_id == customer_id
        ).order_by(Load.created_at.desc()).offset(skip).limit(limit).all()

    def get_unbilled_loads(self) -> List[Load]:
        """Get delivered loads that have no invoiced charges yet."""
        billed_load_ids = self.db.query(Charge.load_id).filter(
            Charge.invoice_id.isnot(None)
        ).distinct()
        return self.db.query(Load).filter(
            Load.actual_delivery_date.isnot(None),
            ~Load.id.in_(billed_load_ids)
        ).order_by(Load.actual_delivery_date.asc()).all()
