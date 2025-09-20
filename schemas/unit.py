# schemas/unit.py
from pydantic import BaseModel, Field
from typing import Optional


class UnitCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32, description="Short unit code, e.g., g, ml, cup")
    display_name: Optional[str] = Field(None, max_length=100, description="Human-readable name, e.g., gram")
    is_metric: bool = Field(False, description="True if metric (g, kg, ml, l)")

class UnitOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    code: str
    display_name: Optional[str] = None
    is_metric: bool