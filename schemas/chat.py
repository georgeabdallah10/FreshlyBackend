from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Literal
from enum import Enum


class ChatMessageBase(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessage(ChatMessageBase):
    id: int
    conversation_id: int
    created_at: datetime
    is_internal: int = 0  # 0 = visible, 1 = internal/hidden from frontend

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


# Image Generation schemas
class ImageGenerationRequest(BaseModel):
    prompt: str
    size: Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"] = "1024x1024"
    quality: Literal["standard", "hd"] = "standard"
    style: Literal["vivid", "natural"] = "vivid"


class ImageGenerationResponse(BaseModel):
    image_url: str
    prompt: str


# Grocery item schemas for image scanning
class GroceryItem(BaseModel):
    name: str
    quantity: str  # e.g., "2 lbs", "3 pieces", "1 bottle"
    category: str  # e.g., "fruits", "vegetables", "dairy", "meat", etc.
    confidence: float = Field(ge=0.0, le=1.0, description="AI confidence score")


class ImageScanRequest(BaseModel):
    image_data: str  # Base64 encoded image


class ImageScanResponse(BaseModel):
    items: List[GroceryItem]
    total_items: int
    analysis_notes: Optional[str] = None  # Any additional AI observations
