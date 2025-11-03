from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .user import UserOut

class MembershipOut(BaseModel):
    id: int
    family_id: int
    user_id: int
    role: str = Field(pattern="^(owner|admin|member)$")
    joined_at: datetime
    user: UserOut  # Nested user object
    
    class Config: 
        from_attributes = True