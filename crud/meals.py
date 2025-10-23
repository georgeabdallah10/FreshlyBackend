# crud/meals.py
from sqlalchemy.orm import Session
from models.meal import Meal
from schemas.meal import MealCreate

def list_meals(db: Session, created_by_user_id: int):
    return db.query(Meal).filter(Meal.created_by_user_id == created_by_user_id).all()

def get_meal(db: Session, meal_id: int):
    return db.query(Meal).get(meal_id)

def create_meal(db: Session, data: MealCreate, created_by_user_id: int):
    meal = Meal(
        created_by_user_id=created_by_user_id,
        name=data.name,
        image=data.image,
        calories=data.calories,
        prep_time=data.prep_time,
        cook_time=data.cook_time,
        total_time=data.total_time,
        meal_type=data.meal_type,
        cuisine=data.cuisine,
        tags=data.tags,
        macros=data.macros.model_dump(),
        difficulty=data.difficulty,
        servings=data.servings,
        diet_compatibility=data.diet_compatibility,
        goal_fit=data.goal_fit,
        ingredients=[i.model_dump(by_alias=False) for i in data.ingredients],
        instructions=data.instructions,
        cooking_tools=data.cooking_tools,
        notes=data.notes,
        is_favorite=data.is_favorite,
    )
    db.add(meal); db.commit(); db.refresh(meal)
    return meal

def update_meal(db: Session, meal: Meal, data: MealCreate):
    for k, v in data.model_dump(by_alias=False).items():
        setattr(meal, k if k not in ("macros", "ingredients", "cooking_tools","diet_compatibility","goal_fit") else k, v)
    db.add(meal); db.commit(); db.refresh(meal)
    return meal

def delete_meal(db: Session, meal: Meal):
    db.delete(meal); db.commit()