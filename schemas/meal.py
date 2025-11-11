# schemas/meal.py
from pydantic import BaseModel, Field
from typing import List, Literal, Dict

class MacroBreakdown(BaseModel):
    protein: int
    fats: int
    carbs: int

class IngredientIn(BaseModel):
    name: str
    amount: str
    in_pantry: bool = Field(default=False, alias="inPantry")

class MealCreate(BaseModel):
    name: str
    image: str
    calories: int
    prep_time: int = Field(alias="prepTime")
    cook_time: int = Field(alias="cookTime")
    total_time: int = Field(alias="totalTime")
    meal_type: Literal["Breakfast","Lunch","Dinner","Snack","Dessert"] = Field(alias="mealType")
    cuisine: str
    tags: List[str]
    macros: MacroBreakdown
    difficulty: Literal["Easy","Medium","Hard"]
    servings: int
    diet_compatibility: List[str] = Field(alias="dietCompatibility")
    goal_fit: List[str] = Field(alias="goalFit")
    ingredients: List[IngredientIn]
    instructions: List[str]
    cooking_tools: List[str] = Field(alias="cookingTools")
    notes: str = ""
    is_favorite: bool = Field(alias="isFavorite", default=False)
    family_id: int | None = Field(alias="familyId", default=None)  # Optional family ownership

    class Config:
        populate_by_name = True

class MealOut(MealCreate):
    id: int
    created_by_user_id: int = Field(alias="createdByUserId")
    model_config = {"from_attributes": True, "populate_by_name": True}
    
class AttachFamilyRequest(BaseModel):
    family_id: int = Field(alias="familyId")
    
    class Config:
        populate_by_name = True
