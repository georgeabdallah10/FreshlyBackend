# schemas/ingredient.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class IngredientCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120, description="Unique ingredient name, e.g., 'olive oil'")
    category: Optional[str] = Field(
        None,
        max_length=80,
        description="Optional category, e.g., 'produce', 'dairy', 'spices'"
    )


class IngredientUpdate(BaseModel):
    # For PATCH/PUT if you allow editing later
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    category: Optional[str] = Field(None, max_length=80)


class IngredientOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    category: Optional[str] = None
    created_at: datetime