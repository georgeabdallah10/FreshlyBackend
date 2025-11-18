from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
from typing import Optional
from .user import UserOut

class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: int
    family_id: int
    user_id: int
    role: str = Field(pattern="^(owner|admin|member)$")
    joined_at: Optional[datetime] = None
    user: Optional[UserOut] = None  # Nested user object


class MembershipRoleUpdate(BaseModel):
    role: str = Field(pattern="^(owner|admin|member)$")
