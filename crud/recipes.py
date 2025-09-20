# crud/recipes.py
from sqlalchemy.orm import Session
from sqlalchemy import asc
from models.recipe import Recipe


def list_recipes(
    db: Session,
    *,
    family_id: int | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Recipe]:
    query = db.query(Recipe).order_by(asc(Recipe.title))
    if family_id is not None:
        query = query.filter(Recipe.family_id == family_id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Recipe.title.ilike(like))
    return query.limit(limit).offset(offset).all()


def get_recipe(db: Session, recipe_id: int) -> Recipe | None:
    return db.query(Recipe).filter(Recipe.id == recipe_id).first()


def create_recipe(
    db: Session,
    *,
    family_id: int,
    title: str,
    description: str | None,
    instructions: str | None,
    servings: int | None,
    created_by_user_id: int | None,
) -> Recipe:
    rec = Recipe(
        family_id=family_id,
        title=title,
        description=description,
        instructions=instructions,
        servings=servings,
        created_by_user_id=created_by_user_id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def update_recipe(
    db: Session,
    recipe: Recipe,
    *,
    title: str | None = None,
    description: str | None = None,
    instructions: str | None = None,
    servings: int | None = None,
) -> Recipe:
    if title is not None:
        recipe.title = title
    if description is not None:
        recipe.description = description
    if instructions is not None:
        recipe.instructions = instructions
    if servings is not None:
        recipe.servings = servings

    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def delete_recipe(db: Session, recipe: Recipe) -> None:
    db.delete(recipe)
    db.commit()