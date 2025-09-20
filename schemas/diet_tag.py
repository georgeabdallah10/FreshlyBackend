# schemas/diet_tag.py
from pydantic import BaseModel, Field


class DietTagCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Short code, e.g., vegan, gluten_free")
    display_name: str = Field(..., max_length=100, description="Human-friendly name, e.g., Vegan")


class DietTagOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    display_name: str