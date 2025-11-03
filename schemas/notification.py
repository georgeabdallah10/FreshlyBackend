# schemas/notification.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class NotificationCreate(BaseModel):
    """Schema for creating a notification"""
    user_id: int = Field(alias="userId")
    type: Literal[
        "meal_share_request",
        "meal_share_accepted", 
        "meal_share_declined",
        "family_invite",
        "family_member_joined",
        "system"
    ]
    title: str
    message: str
    related_meal_id: Optional[int] = Field(alias="relatedMealId", default=None)
    related_user_id: Optional[int] = Field(alias="relatedUserId", default=None)
    related_family_id: Optional[int] = Field(alias="relatedFamilyId", default=None)
    related_share_request_id: Optional[int] = Field(alias="relatedShareRequestId", default=None)
    
    class Config:
        populate_by_name = True


class NotificationOut(BaseModel):
    """Schema for notification output"""
    id: int
    user_id: int = Field(alias="userId")
    type: Literal[
        "meal_share_request",
        "meal_share_accepted",
        "meal_share_declined", 
        "family_invite",
        "family_member_joined",
        "system"
    ]
    title: str
    message: str
    related_meal_id: Optional[int] = Field(alias="relatedMealId", default=None)
    related_user_id: Optional[int] = Field(alias="relatedUserId", default=None)
    related_family_id: Optional[int] = Field(alias="relatedFamilyId", default=None)
    related_share_request_id: Optional[int] = Field(alias="relatedShareRequestId", default=None)
    is_read: bool = Field(alias="isRead")
    created_at: datetime = Field(alias="createdAt")
    read_at: Optional[datetime] = Field(alias="readAt", default=None)
    
    # Optional related data
    related_user_name: Optional[str] = Field(alias="relatedUserName", default=None)
    related_meal_name: Optional[str] = Field(alias="relatedMealName", default=None)
    related_family_name: Optional[str] = Field(alias="relatedFamilyName", default=None)
    
    class Config:
        populate_by_name = True
        from_attributes = True


class NotificationUpdate(BaseModel):
    """Schema for updating notification read status"""
    is_read: bool = Field(alias="isRead")
    
    class Config:
        populate_by_name = True


class NotificationStats(BaseModel):
    """Schema for notification statistics"""
    total: int
    unread: int
    unread_by_type: dict = Field(alias="unreadByType")
    
    class Config:
        populate_by_name = True
