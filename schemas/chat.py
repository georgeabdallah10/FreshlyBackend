from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class ChatMessageBase(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessage(ChatMessageBase):
    id: int
    conversation_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatConversationBase(BaseModel):
    title: Optional[str] = None


class ChatConversationCreate(ChatConversationBase):
    pass


class ChatConversation(ChatConversationBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage] = []

    class Config:
        from_attributes = True


class ChatConversationSummary(BaseModel):
    """Lightweight version without messages for listing conversations"""
    id: int
    user_id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: int

    class Config:
        from_attributes = True


# Request/Response schemas
class ChatRequest(BaseModel):
    prompt: str
    system: Optional[str] = None
    conversation_id: Optional[int] = None  # If None, creates new conversation


class ChatResponse(BaseModel):
    reply: str
    conversation_id: int
    message_id: int
