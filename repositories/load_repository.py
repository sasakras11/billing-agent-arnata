"""Repository for load operations."""
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session

from models import Load
from repositories.base import BaseRepository
from logging_config import get_logger

logger = get_logger(__name__)


class LoadRepository(BaseRepository[Load]):
    """Repository for load-specific database operations."""
    
    def __init__(self, db: Session):
        """
        Initialize load repository.
        
        Args:
            db: Database session
        """
        super().__init__(Load, db)
    
    def get_by_load_number(self, load_number: str) -> Optional[Load]:
        """
        Get load by load number.
        
        Args:
            load_number: Load number
            
        Returns:
            Load or None
        """
        return self.db.query(Load).filter(
            Load.load_number == load_number
        ).first()
    
    def get_by_customer(
        self,
        customer_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Load]:
        """
        Get loads for a customer.
        
        Args:
            customer_id: Customer ID
            skip: Pagination offset
            limit: Page size
            
        Returns:
            List of loads
        """
        return self.db.query(Load).filter(
            Load.customer_id == customer_id
        ).order_by(Load.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_unbilled_loads(self) -> List[Load]:
        """
        Get loads that haven't been billed yet.
        
        Returns:
            List of unbilled loads
        """
        return self.db.query(Load).filter(
            Load.invoice_id.is_(None),
            Load.delivered_date.isnot(None)
        ).order_by(Load.delivered_date.asc()).all()

