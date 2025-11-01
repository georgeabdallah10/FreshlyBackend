from sqlalchemy import Column, Integer, Text, DateTime, func, Boolean, String, text
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
import sqlalchemy as sa
from core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, index=True, nullable=False)
    name = Column(Text, nullable=True)
    phone_number= Column(Text, nullable=True)
    location = sa.Column(sa.String(255), nullable=True) 
    hashed_password = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    avatar_path = Column(String, nullable=True)
    status = Column(sa.String(50), nullable=False, server_default="active")
    
    password_reset_code = Column(String(6), nullable=True, index=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_attempts = Column(Integer, nullable=False, default=0)
    
    is_verified = Column(Boolean, nullable=False, server_default=text("false"), default=False)
    verification_code = Column(String(6), nullable=True, index=True)
    verification_expires_at = Column(DateTime(timezone=True), nullable=True)    

    # Family memberships
    memberships = relationship(
        "FamilyMembership",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # User → MealPlan (creator)
    created_meal_plans = relationship(
        "MealPlan",
        back_populates="created_by",
        cascade="all, delete-orphan",
         foreign_keys="[MealPlan.created_by_user_id]",  # <-- disambiguate
        lazy="selectin",
    )
    
    personal_pantry_items = relationship(
    "PantryItem",
    back_populates="owner",
    foreign_keys="PantryItem.owner_user_id",
    cascade="all, delete-orphan"
    )

    # User → UserPreference (one-to-one, singular: preference)
    preference = relationship(
        "UserPreference",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    meals_created = relationship("Meal", back_populates="created_by")
    
    # Chat conversations
    chat_conversations = relationship(
        "ChatConversation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"