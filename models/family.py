from sqlalchemy import Column, Integer, Text, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base

class Family(Base):
    __tablename__ = "families"
    id = Column(Integer, primary_key=True)
    display_name = Column(Text, nullable=False)
    invite_code = Column(Text, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    memberships = relationship("FamilyMembership", back_populates="family", cascade="all, delete-orphan")