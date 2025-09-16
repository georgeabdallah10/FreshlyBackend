from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from models.base import Base

class FamilyMembership(Base):
    __tablename__ = "family_memberships"
    __table_args__ = (
        UniqueConstraint("family_id", "user_id", name="uq_family_user"),
        CheckConstraint("role IN ('owner','admin','member')", name="ck_membership_role"),
    )
    id = Column(Integer, primary_key=True)
    family_id = Column(Integer, ForeignKey("families.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    family = relationship("Family", back_populates="memberships")
    user = relationship("User", back_populates="memberships")