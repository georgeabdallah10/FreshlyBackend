from sqlalchemy import Column, Integer, Text, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, index=True, nullable=False)
    name = Column(Text, nullable=True)
    hashed_password = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    memberships = relationship("FamilyMembership", back_populates="user", cascade="all, delete-orphan")