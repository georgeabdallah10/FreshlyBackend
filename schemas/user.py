from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from .user_preference import UserPreferenceOut



class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    tier: Optional[str] = Field(None, min_length=1, max_length=32)
    avatar_path: Optional[str] = None
    gender: Optional[str] = Field(None, min_length=1, max_length=32)
    age: Optional[int] = Field(None, ge=0)
    weight: Optional[float] = Field(None, gt=0)
    height: Optional[float] = Field(None, gt=0)
    calories: Optional[float] = Field(None, gt=0)

    @field_validator("name", "phone_number", "location", "status", "tier", "avatar_path", "gender")
    @classmethod
    def _strip(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        return v if v != "" else None  # empty strings become None (won’t update)

class UserOut(BaseModel):
    id: int
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "user"
    tier: Optional[str] = "free"
    avatar_path: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    calories: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    

    class Config:
        from_attributes = True
