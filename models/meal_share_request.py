# models/meal_share_request.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.db import Base
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


class MealShareRequest(Base):
    __tablename__ = "meal_share_requests"

    id = Column(Integer, primary_key=True)

    # Foreign Keys
    meal_id = Column(Integer, ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=True, index=True)
    accepted_meal_id = Column(Integer, ForeignKey("meals.id", ondelete="SET NULL"), nullable=True)

    # Request status: pending, accepted, declined
    status = Column(
        ENUM(
            "pending",
            "accepted",
            "declined",
            name="meal_share_request_status",
            create_type=False       # <---- CRUCIAL FIX
        ),
        nullable=False,
        create_type=False,
        default="pending",
        index=True
    )
    
    # Optional message from sender
    message = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    meal = relationship("Meal", foreign_keys=[meal_id], lazy="selectin")
    accepted_meal = relationship("Meal", foreign_keys=[accepted_meal_id], lazy="selectin", post_update=True)
    sender = relationship("User", foreign_keys=[sender_user_id], lazy="selectin")
    recipient = relationship("User", foreign_keys=[recipient_user_id], lazy="selectin")
    family = relationship("Family", lazy="selectin")

    __table_args__ = (
        # Composite indexes for common meal share request queries
        Index('idx_msr_recipient_status', 'recipient_user_id', 'status'),
        Index('idx_msr_family_status_created', 'family_id', 'status', 'created_at'),
        Index('idx_msr_sender_created', 'sender_user_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<MealShareRequest id={self.id} meal_id={self.meal_id} status={self.status}>"