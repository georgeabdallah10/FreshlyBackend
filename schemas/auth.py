from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional
from .user_preference import UserPreferenceCreate

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(..., max_length=72)
    name: str | None = None
    phone_number: str | None = None
    model_config = ConfigDict(from_attributes=True)
    preference: Optional[UserPreferenceCreate] = Field(default=None, alias="preference")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,  # allows using either "preference" or its alias "preferences"
    }


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    model_config = ConfigDict(from_attributes=True)

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    model_config = ConfigDict(from_attributes=True)