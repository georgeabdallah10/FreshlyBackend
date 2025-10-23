from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from .user_preference import UserPreferenceOut



class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    avatar_path: Optional[str] = None

    @field_validator("name", "phone_number", "location", "status", "avatar_path")
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
    avatar_path: Optional[str] = None
    

    class Config:
        orm_mode = True