from sqlalchemy import (
    Column, Integer, Text, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.db import Base

class FamilyMembership(Base):
    __tablename__ = "family_memberships"

    id = Column(Integer, primary_key=True)

    # FKs
    family_id = Column(
        Integer,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # role & timestamps
    role = Column(Text, nullable=False)  # 'owner' | 'admin' | 'member'
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ORM relationships (match Family.memberships back_populates)
    family = relationship("Family", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('owner','admin','member')", name="ck_memberships_role"),
        UniqueConstraint("family_id", "user_id", name="uq_membership_family_user"),
    )

    def __repr__(self) -> str:
        return f"<FamilyMembership id={self.id} family_id={self.family_id} user_id={self.user_id} role={self.role!r}>"