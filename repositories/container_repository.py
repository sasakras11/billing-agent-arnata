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
        """
        Initialize container repository.
        
        Args:
            db: Database session
        """
        super().__init__(Container, db)
    
    def get_by_container_number(self, container_number: str) -> Optional[Container]:
        """
        Get container by container number.
        
        Args:
            container_number: Container number
            
        Returns:
            Container or None
        """
        return self.db.query(Container).filter(
            Container.container_number == container_number.upper()
        ).first()
    
    def get_active_containers(self) -> List[Container]:
        """
        Get all active containers (not yet returned).
        
        Returns:
            List of active containers
        """
        return self.db.query(Container).filter(
            Container.returned_empty.is_(None)
        ).order_by(Container.vessel_discharged.desc()).all()
    
    def get_containers_needing_return(
        self,
        before_date: Optional[date] = None
    ) -> List[Container]:
        """
        Get containers that need to be returned soon.
        
        Args:
            before_date: Containers with per diem starting before this date
            
        Returns:
            List of containers
        """
        if before_date is None:
            before_date = date.today()
        
        return self.db.query(Container).filter(
            and_(
                Container.per_diem_starts <= before_date,
                Container.returned_empty.is_(None)
            )
        ).order_by(Container.per_diem_starts.asc()).all()
    
    def get_containers_with_charges(self) -> List[Container]:
        """
        Get containers that currently have active charges.
        
        Returns:
            List of containers
        """
        return self.db.query(Container).filter(
            and_(
                Container.picked_up.isnot(None),
                Container.returned_empty.is_(None),
                Container.per_diem_starts.isnot(None)
            )
        ).all()

