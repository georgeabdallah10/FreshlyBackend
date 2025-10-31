"""
Base repository pattern for data access layer
Provides common CRUD operations and query patterns
"""
import logging
from typing import Type, TypeVar, Generic, List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, desc, asc
from fastapi import HTTPException, status

from core.db import Base

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations"""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """Get a single record by ID"""
        try:
            return db.query(self.model).filter(self.model.id == id).first()
        except Exception as e:
            logger.error(f"Error getting {self.model.__name__} with id {id}: {e}")
            return None

    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False
    ) -> List[ModelType]:
        """Get multiple records with filtering and pagination"""
        try:
            query = db.query(self.model)
            
            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        if isinstance(value, list):
                            query = query.filter(getattr(self.model, field).in_(value))
                        else:
                            query = query.filter(getattr(self.model, field) == value)
            
            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                order_column = getattr(self.model, order_by)
                if order_desc:
                    query = query.order_by(desc(order_column))
                else:
                    query = query.order_by(asc(order_column))
            
            return query.offset(skip).limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error getting multiple {self.model.__name__}: {e}")
            return []

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """Create a new record"""
        try:
            db_obj = self.model(**obj_in)
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.info(f"Created {self.model.__name__} with id {db_obj.id}")
            return db_obj
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity violation"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error creating record"
            )

    def update(
        self, 
        db: Session, 
        *, 
        db_obj: ModelType, 
        obj_in: Dict[str, Any]
    ) -> ModelType:
        """Update an existing record"""
        try:
            for field, value in obj_in.items():
                if hasattr(db_obj, field) and value is not None:
                    setattr(db_obj, field, value)
            
            db.commit()
            db.refresh(db_obj)
            logger.info(f"Updated {self.model.__name__} with id {db_obj.id}")
            return db_obj
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error updating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity violation"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating record"
            )

    def delete(self, db: Session, *, id: int) -> bool:
        """Delete a record by ID"""
        try:
            obj = db.query(self.model).get(id)
            if not obj:
                return False
            
            db.delete(obj)
            db.commit()
            logger.info(f"Deleted {self.model.__name__} with id {id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting {self.model.__name__} with id {id}: {e}")
            return False

    def soft_delete(self, db: Session, *, id: int) -> bool:
        """Soft delete a record (if model supports it)"""
        try:
            obj = db.query(self.model).get(id)
            if not obj:
                return False
            
            # Check if model has soft delete fields
            if hasattr(obj, 'is_deleted'):
                obj.is_deleted = True
                if hasattr(obj, 'deleted_at'):
                    from datetime import datetime
                    obj.deleted_at = datetime.now()
                db.commit()
                logger.info(f"Soft deleted {self.model.__name__} with id {id}")
                return True
            else:
                # Fall back to hard delete
                return self.delete(db, id=id)
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error soft deleting {self.model.__name__} with id {id}: {e}")
            return False

    def count(self, db: Session, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count records with optional filters"""
        try:
            query = db.query(self.model)
            
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.filter(getattr(self.model, field) == value)
            
            return query.count()
            
        except Exception as e:
            logger.error(f"Error counting {self.model.__name__}: {e}")
            return 0

    def exists(self, db: Session, id: int) -> bool:
        """Check if record exists"""
        try:
            return db.query(self.model).filter(self.model.id == id).first() is not None
        except Exception as e:
            logger.error(f"Error checking existence of {self.model.__name__} with id {id}: {e}")
            return False

    def bulk_create(self, db: Session, *, objects: List[Dict[str, Any]]) -> List[ModelType]:
        """Create multiple records in bulk"""
        try:
            db_objects = [self.model(**obj) for obj in objects]
            db.add_all(db_objects)
            db.commit()
            
            for obj in db_objects:
                db.refresh(obj)
            
            logger.info(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error in bulk create {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data integrity violation in bulk operation"
            )
        except Exception as e:
            db.rollback()
            logger.error(f"Error in bulk create {self.model.__name__}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error in bulk create operation"
            )

    def search(
        self, 
        db: Session, 
        query: str, 
        fields: List[str],
        limit: int = 20
    ) -> List[ModelType]:
        """Search records across multiple fields"""
        try:
            db_query = db.query(self.model)
            
            # Build OR conditions for each field
            conditions = []
            for field in fields:
                if hasattr(self.model, field):
                    field_attr = getattr(self.model, field)
                    conditions.append(field_attr.ilike(f"%{query}%"))
            
            if conditions:
                db_query = db_query.filter(or_(*conditions))
            
            return db_query.limit(limit).all()
            
        except Exception as e:
            logger.error(f"Error searching {self.model.__name__}: {e}")
            return []
