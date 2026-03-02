"""Repository for customer operations."""
from typing import List, Optional

from sqlalchemy.orm import Session

from models import Customer
from repositories.base import BaseRepository
from logging_config import get_logger

logger = get_logger(__name__)


class CustomerRepository(BaseRepository[Customer]):
    """Repository for customer-specific database operations."""

    def __init__(self, db: Session):
        super().__init__(Customer, db)

    def get_by_name(self, name: str) -> Optional[Customer]:
        """Get customer by name."""
        return self.db.query(Customer).filter(Customer.name == name).first()

    def get_by_quickbooks_id(self, quickbooks_id: str) -> Optional[Customer]:
        """Get customer by QuickBooks customer ID."""
        return self.db.query(Customer).filter(
            Customer.quickbooks_customer_id == quickbooks_id
        ).first()

    def get_active_customers(self) -> List[Customer]:
        """Get all active customers."""
        return self.db.query(Customer).filter(
            Customer.is_active == True
        ).order_by(Customer.name.asc()).all()

    def search_by_name(self, search_term: str) -> List[Customer]:
        """Search customers by name (case-insensitive)."""
        return self.db.query(Customer).filter(
            Customer.name.ilike(f"%{search_term}%")
        ).order_by(Customer.name.asc()).all()
