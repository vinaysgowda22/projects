"""Base repository class with common CRUD operations."""

from typing import Generic, List, Optional, Type, TypeVar

from loguru import logger
from sqlalchemy.orm import Session

from backend.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType], session: Session):
        """Initialize repository with model class and session."""
        self.model = model
        self.session = session
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.flush()
        logger.debug(f"Created {self.model.__name__}: {obj}")
        return obj
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """Get a record by ID."""
        return self.session.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[ModelType]:
        """Get all records with optional pagination."""
        query = self.session.query(self.model)
        if limit:
            query = query.limit(limit)
        return query.offset(offset).all()
    
    def update(self, obj: ModelType, **kwargs) -> ModelType:
        """Update a record."""
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        self.session.flush()
        logger.debug(f"Updated {self.model.__name__} id={obj.id}")
        return obj
    
    def delete(self, obj: ModelType) -> None:
        """Delete a record."""
        self.session.delete(obj)
        self.session.flush()
        logger.debug(f"Deleted {self.model.__name__} id={obj.id}")
    
    def count(self) -> int:
        """Count all records."""
        return self.session.query(self.model).count()
