# schemas/recipe_ingredient.py
from pydantic import BaseModel, Field
from typing import Optional


class RecipeIngredientCreate(BaseModel):
    recipe_id: int = Field(..., description="The recipe this ingredient belongs to")
    ingredient_id: int = Field(..., description="Ingredient reference")
    quantity: Optional[float] = Field(None, ge=0, description="Quantity of the ingredient")
    unit_id: Optional[int] = Field(None, description="Unit for the quantity, e.g. grams, ml")
    notes: Optional[str] = Field(None, description="Optional line-item notes")


class RecipeIngredientUpdate(BaseModel):
    quantity: Optional[float] = Field(None, ge=0)
    unit_id: Optional[int] = Field(None)
    notes: Optional[str] = Field(None)


class RecipeIngredientOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    recipe_id: int
    ingredient_id: int
    quantity: Optional[float] = None
    unit_id: Optional[int] = None
    notes: Optional[str] = None