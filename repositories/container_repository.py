"""Repository for container operations."""
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import Container
from repositories.base import BaseRepository
from logging_config import get_logger

logger = get_logger(__name__)


class ContainerRepository(BaseRepository[Container]):
    """Repository for container-specific database operations."""

    def __init__(self, db: Session):
        super().__init__(Container, db)

    def get_by_container_number(self, container_number: str) -> Optional[Container]:
        """Get container by container number."""
        return self.db.query(Container).filter(
            Container.container_number == container_number.upper()
        ).first()

    def get_active_containers(self) -> List[Container]:
        """Get all active containers (not yet returned)."""
        return self.db.query(Container).filter(
            Container.returned_empty.is_(None)
        ).order_by(Container.vessel_discharged.desc()).all()

    def get_containers_needing_return(self, before_date: Optional[date] = None) -> List[Container]:
        """Get containers with per diem starting before before_date."""
        if before_date is None:
            before_date = date.today()
        return self.db.query(Container).filter(
            and_(
                Container.per_diem_starts <= before_date,
                Container.returned_empty.is_(None),
            )
        ).order_by(Container.per_diem_starts.asc()).all()

    def get_containers_with_charges(self) -> List[Container]:
        """Get containers that currently have active charges."""
        return self.db.query(Container).filter(
            and_(
                Container.picked_up.isnot(None),
                Container.returned_empty.is_(None),
                Container.per_diem_starts.isnot(None),
            )
        ).all()
