from pydantic import BaseModel, EmailStr
class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str | None = None
    class Config: from_attributes = True