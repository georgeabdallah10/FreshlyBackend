"""
User service layer for handling user-related business logic
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models.user import User
from schemas.user import UserCreate, UserUpdate
from core.security import hash_password
from utils.cache import cached
import crud.users as user_crud

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user-related operations"""

    @cached(ttl=300, key_prefix="user_profile")
    async def get_user_profile(self, db: Session, user_id: int) -> Optional[User]:
        """Get user profile with caching"""
        user = user_crud.get_user(db, user_id)
        if not user:
            logger.warning(f"User profile not found: {user_id}")
            return None
        
        logger.info(f"Retrieved user profile: {user_id}")
        return user

    async def update_user_profile(
        self, 
        db: Session, 
        user_id: int, 
        update_data: UserUpdate
    ) -> User:
        """Update user profile and invalidate cache"""
        user = user_crud.get_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update user data
        updated_user = user_crud.update_user(db, user_id, update_data)
        
        # Invalidate cache
        from utils.cache import invalidate_cache_pattern
        await invalidate_cache_pattern(f"user_profile:*:{user_id}:*")
        
        logger.info(f"User profile updated: {user_id}")
        return updated_user

    async def deactivate_user(self, db: Session, user_id: int) -> bool:
        """Deactivate user account"""
        user = user_crud.get_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Update user status to inactive
        user_crud.update_user(db, user_id, UserUpdate(status="inactive"))
        
        # Invalidate all user-related cache
        from utils.cache import invalidate_cache_pattern
        await invalidate_cache_pattern(f"*:{user_id}:*")
        
        logger.info(f"User deactivated: {user_id}")
        return True

    @cached(ttl=600, key_prefix="user_stats")
    async def get_user_statistics(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get user statistics with caching"""
        # This would typically aggregate data from multiple tables
        stats = {
            "total_meals_planned": 0,
            "favorite_recipes_count": 0,
            "family_members": 0,
            "pantry_items": 0,
            "chat_conversations": 0
        }
        
        # Mock implementation - replace with actual queries
        try:
            # Count meal plans
            # stats["total_meals_planned"] = db.query(MealPlan).filter_by(user_id=user_id).count()
            
            # Count family members
            # stats["family_members"] = db.query(FamilyMembership).filter_by(user_id=user_id).count()
            
            # Count pantry items
            # stats["pantry_items"] = db.query(PantryItem).filter_by(owner_user_id=user_id).count()
            
            # Count chat conversations
            # stats["chat_conversations"] = db.query(ChatConversation).filter_by(user_id=user_id).count()
            
            logger.info(f"Retrieved user statistics: {user_id}")
            return stats
            
        except Exception as e:
            logger.error(f"Error retrieving user statistics for {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving user statistics"
            )

    async def check_user_permissions(
        self, 
        db: Session, 
        user_id: int, 
        resource_type: str, 
        resource_id: int
    ) -> bool:
        """Check if user has permission to access a resource"""
        try:
            if resource_type == "meal_plan":
                # Check if user owns the meal plan or is a family member
                # meal_plan = db.query(MealPlan).filter_by(id=resource_id).first()
                # return meal_plan and (meal_plan.created_by_user_id == user_id or user_in_family)
                pass
            
            elif resource_type == "pantry_item":
                # Check if user owns the pantry item
                # pantry_item = db.query(PantryItem).filter_by(id=resource_id).first()
                # return pantry_item and pantry_item.owner_user_id == user_id
                pass
            
            elif resource_type == "chat_conversation":
                # Check if user owns the conversation
                # conversation = db.query(ChatConversation).filter_by(id=resource_id).first()
                # return conversation and conversation.user_id == user_id
                pass
            
            # Default deny
            return False
            
        except Exception as e:
            logger.error(f"Error checking permissions for user {user_id}: {e}")
            return False

    async def get_user_preferences_summary(
        self, 
        db: Session, 
        user_id: int
    ) -> Dict[str, Any]:
        """Get summary of user preferences for quick access"""
        try:
            # This would typically join user preferences with diet tags, etc.
            summary = {
                "dietary_restrictions": [],
                "favorite_cuisines": [],
                "cooking_skill_level": "beginner",
                "meal_prep_time_preference": "30_minutes",
                "family_size": 1
            }
            
            logger.info(f"Retrieved user preferences summary: {user_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error retrieving user preferences for {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error retrieving user preferences"
            )

    async def search_users(
        self, 
        db: Session, 
        query: str, 
        limit: int = 20
    ) -> List[User]:
        """Search users by name or email (admin function)"""
        try:
            # This would be an admin-only function
            users = user_crud.search_users(db, query, limit)
            logger.info(f"User search performed: '{query}' - {len(users)} results")
            return users
            
        except Exception as e:
            logger.error(f"Error searching users with query '{query}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error searching users"
            )


# Global service instance
user_service = UserService()
