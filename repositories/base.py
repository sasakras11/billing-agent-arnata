"""Base repository with common database operations."""
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from exceptions import DatabaseError
from logging_config import get_logger

logger = get_logger(__name__)

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository providing common CRUD operations."""

    def __init__(self, model: Type[ModelType], db: Session):
        """Initialize repository with model and session."""
        self.model = model
        self.db = db

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get entity by ID."""
        try:
            return self.db.query(self.model).filter(
                self.model.id == id
            ).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} by ID {id}: {e}")
            raise DatabaseError(f"Failed to get {self.model.__name__}") from e
    
    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Optional[str] = None,
        order_direction: str = "desc"
    ) -> List[ModelType]:
        """Get all entities with pagination."""
        try:
            query = self.db.query(self.model)
            
            # Apply ordering
            if order_by:
                order_field = getattr(self.model, order_by, None)
                if order_field is not None:
                    if order_direction == "asc":
                        query = query.order_by(asc(order_field))
                    else:
                        query = query.order_by(desc(order_field))
            
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting all {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to get {self.model.__name__} list") from e
    
    def create(self, **kwargs) -> ModelType:
        """Create new entity."""
        try:
            entity = self.model(**kwargs)
            self.db.add(entity)
            self.db.commit()
            self.db.refresh(entity)
            
            logger.info(f"Created {self.model.__name__} with ID {entity.id}")
            return entity
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to create {self.model.__name__}") from e
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update entity by ID."""
        try:
            entity = self.get_by_id(id)
            
            if not entity:
                return None
            
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            
            self.db.commit()
            self.db.refresh(entity)
            
            logger.info(f"Updated {self.model.__name__} with ID {id}")
            return entity
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating {self.model.__name__} {id}: {e}")
            raise DatabaseError(f"Failed to update {self.model.__name__}") from e
    
    def delete(self, id: int) -> bool:
        """Delete entity by ID."""
        try:
            entity = self.get_by_id(id)
            
            if not entity:
                return False
            
            self.db.delete(entity)
            self.db.commit()
            
            logger.info(f"Deleted {self.model.__name__} with ID {id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting {self.model.__name__} {id}: {e}")
            raise DatabaseError(f"Failed to delete {self.model.__name__}") from e
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filters."""
        try:
            query = self.db.query(self.model)
            
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)
            
            return query.count()
            
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to count {self.model.__name__}") from e
    
    def exists(self, id: int) -> bool:
        """Check if entity exists by ID."""
        try:
            return self.db.query(self.model).filter(
                self.model.id == id
            ).count() > 0
        except Exception as e:
            logger.error(f"Error checking {self.model.__name__} existence: {e}")
            raise DatabaseError(f"Failed to check {self.model.__name__} existence") from e
    
    def bulk_create(self, entities: List[Dict[str, Any]]) -> List[ModelType]:
        """Bulk create entities."""
        try:
            created = []
            
            for entity_data in entities:
                entity = self.model(**entity_data)
                self.db.add(entity)
                created.append(entity)
            
            self.db.commit()
            
            for entity in created:
                self.db.refresh(entity)
            
            logger.info(f"Bulk created {len(created)} {self.model.__name__} entities")
            return created
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error bulk creating {self.model.__name__}: {e}")
            raise DatabaseError(f"Failed to bulk create {self.model.__name__}") from e

