from pydantic import BaseModel, Field
class MembershipOut(BaseModel):
    id: int
    family_id: int
    user_id: int
    role: str = Field(pattern="^(owner|admin|member)$")
    class Config: from_attributes = True