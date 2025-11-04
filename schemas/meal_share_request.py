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
    meal_id: int = Field(serialization_alias="mealId")
    sender_user_id: int = Field(serialization_alias="senderUserId")
    recipient_user_id: int = Field(serialization_alias="recipientUserId")
    family_id: int = Field(serialization_alias="familyId")
    status: Literal["pending", "accepted", "declined"]
    message: Optional[str] = None
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
    responded_at: Optional[datetime] = Field(serialization_alias="respondedAt", default=None)
    
    # Nested data
    meal_name: Optional[str] = Field(serialization_alias="mealName", default=None)
    sender_name: Optional[str] = Field(serialization_alias="senderName", default=None)
    recipient_name: Optional[str] = Field(serialization_alias="recipientName", default=None)
    
    model_config = {"from_attributes": True, "populate_by_name": True}


class MealShareRequestResponse(BaseModel):
    """Schema for responding to a meal share request"""
    action: Literal["accept", "decline"]
