from pydantic import BaseModel

class FamilyCreate(BaseModel):
    display_name: str

class FamilyOut(BaseModel):
    id: int
    display_name: str
    invite_code: str
    class Config: from_attributes = True

class JoinByCodeIn(BaseModel):
    invite_code: str