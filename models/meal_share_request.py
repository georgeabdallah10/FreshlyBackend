# models/meal_share_request.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.db import Base


class MealShareRequest(Base):
    __tablename__ = "meal_share_requests"

    id = Column(Integer, primary_key=True)
    
    # Foreign Keys
    meal_id = Column(Integer, ForeignKey("meals.id", ondelete="CASCADE"), nullable=False)
    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    
    # Request status: pending, accepted, declined
    status = Column(
        Enum("pending", "accepted", "declined", name="meal_share_request_status"),
        nullable=False,
        default="pending"
    )
    
    # Optional message from sender
    message = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    meal = relationship("Meal", lazy="selectin")
    sender = relationship("User", foreign_keys=[sender_user_id], lazy="selectin")
    recipient = relationship("User", foreign_keys=[recipient_user_id], lazy="selectin")
    family = relationship("Family", lazy="selectin")

    def __repr__(self) -> str:
        return f"<MealShareRequest id={self.id} meal_id={self.meal_id} status={self.status}>"
