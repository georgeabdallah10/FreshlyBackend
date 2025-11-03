# schemas/meal_share_request.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class MealShareRequestCreate(BaseModel):
    """Schema for creating a meal share request"""
    meal_id: int = Field(alias="mealId")
    recipient_user_id: int = Field(alias="recipientUserId")
    message: Optional[str] = None
    
    class Config:
        populate_by_name = True


class MealShareRequestOut(BaseModel):
    """Schema for meal share request output"""
    id: int
    meal_id: int = Field(alias="mealId")
    sender_user_id: int = Field(alias="senderUserId")
    recipient_user_id: int = Field(alias="recipientUserId")
    family_id: int = Field(alias="familyId")
    status: Literal["pending", "accepted", "declined"]
    message: Optional[str] = None
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    responded_at: Optional[datetime] = Field(alias="respondedAt", default=None)
    
    # Nested data
    meal_name: Optional[str] = Field(alias="mealName", default=None)
    sender_name: Optional[str] = Field(alias="senderName", default=None)
    recipient_name: Optional[str] = Field(alias="recipientName", default=None)
    
    class Config:
        populate_by_name = True
        from_attributes = True


class MealShareRequestResponse(BaseModel):
    """Schema for responding to a meal share request"""
    action: Literal["accept", "decline"]
