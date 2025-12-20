from sqlalchemy import Column, Integer, Text, DateTime, func, String, ForeignKey
from sqlalchemy.orm import relationship
from datetime import timezone
from core.db import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)  # Optional title for the conversation
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # Internal messages are sent to OpenAI but NOT returned to frontend (e.g., assistant intent state)
    is_internal = Column(Integer, default=0, nullable=False)  # 0 = visible, 1 = internal/hidden
    # URL of uploaded image stored in Supabase Storage (nullable for text-only messages)
    image_url = Column(Text, nullable=True)

    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")
