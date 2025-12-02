# models/notification.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.db import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Notification details
    type = Column(
        Enum(
            "meal_share_request",
            "meal_share_accepted",
            "meal_share_declined",
            "family_invite",
            "family_member_joined",
            "system",
            name="notification_type"
        ),
        nullable=False
    )
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Link to related entities (optional)
    related_meal_id = Column(Integer, ForeignKey("meals.id", ondelete="CASCADE"), nullable=True)
    related_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    related_family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=True)
    related_share_request_id = Column(Integer, ForeignKey("meal_share_requests.id", ondelete="CASCADE"), nullable=True)
    
    # Status
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    related_user = relationship("User", foreign_keys=[related_user_id], lazy="selectin")
    related_meal = relationship("Meal", lazy="selectin")
    related_family = relationship("Family", lazy="selectin")
    related_share_request = relationship("MealShareRequest", lazy="selectin")

    __table_args__ = (
        # Composite indexes for common notification queries
        Index('idx_notif_user_read_created', 'user_id', 'is_read', 'created_at'),
        Index('idx_notif_user_created', 'user_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} type={self.type} is_read={self.is_read}>"
