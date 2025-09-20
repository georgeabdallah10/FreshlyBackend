# schemas/recipe.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RecipeCreate(BaseModel):
    family_id: int = Field(..., description="Family this recipe belongs to")
    title: str = Field(..., min_length=2, max_length=200, description="Recipe title")
    description: Optional[str] = Field(None, max_length=500, description="Short description of the recipe")
    instructions: Optional[str] = Field(None, description="Cooking steps, markdown or text")
    servings: Optional[int] = Field(None, ge=1, description="Number of servings this recipe makes")


class RecipeUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    instructions: Optional[str] = Field(None)
    servings: Optional[int] = Field(None, ge=1)


class RecipeOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    family_id: int
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    servings: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime