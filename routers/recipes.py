# routers/recipes.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from models.user import User
from models.membership import FamilyMembership
from schemas.recipe import RecipeCreate, RecipeUpdate, RecipeOut
from crud.recipes import list_recipes, get_recipe, create_recipe, update_recipe, delete_recipe

router = APIRouter(prefix="/recipes", tags=["recipes"])


class ErrorOut(BaseModel):
    detail: str


# ---------- Helpers ----------
def _ensure_member(db: Session, user_id: int, family_id: int) -> None:
    """
    Ensure the user is a member of the given family.
    Raises 403 if not.
    """
    m = (
        db.query(FamilyMembership)
        .filter(FamilyMembership.user_id == user_id, FamilyMembership.family_id == family_id)
        .first()
    )
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this family")


def _ensure_can_edit(db: Session, user_id: int, recipe_family_id: int, recipe_owner_id: int | None) -> None:
    """
    Allow edit if:
      - user is owner/admin of the family, or
      - user created the recipe
    (You can tighten/relax this later.)
    """
    m = (
        db.query(FamilyMembership)
        .filter(FamilyMembership.user_id == user_id, FamilyMembership.family_id == recipe_family_id)
        .first()
    )
    if not m:
        raise HTTPException(status_code=403, detail="Not a member of this family")

    if m.role in ("owner", "admin"):
        return
    if recipe_owner_id and recipe_owner_id == user_id:
        return
    raise HTTPException(status_code=403, detail="Insufficient permissions")


# ---------- Endpoints ----------
@router.get(
    "",
    response_model=list[RecipeOut],
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}},
)
def list_all_recipes(
    family_id: int | None = Query(None, description="Filter by family id"),
    q: str | None = Query(None, description="Search in title (ILIKE)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return list_recipes(db, family_id=family_id, q=q, limit=limit, offset=offset)


@router.get(
    "/{recipe_id}",
    response_model=RecipeOut,
    responses={404: {"model": ErrorOut, "description": "Recipe not found"}},
)
def get_one_recipe(
    recipe_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rec = get_recipe(db, recipe_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return rec


@router.post(
    "",
    response_model=RecipeOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorOut, "description": "Unauthorized"},
        403: {"model": ErrorOut, "description": "Not a member of this family"},
    },
)
def create_one_recipe(
    data: RecipeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Guard: user must be in the recipe's family
    _ensure_member(db, current_user.id, data.family_id)

    rec = create_recipe(
        db,
        family_id=data.family_id,
        title=data.title,
        description=data.description,
        instructions=data.instructions,
        servings=data.servings,
        created_by_user_id=current_user.id,
    )
    return rec


@router.patch(
    "/{recipe_id}",
    response_model=RecipeOut,
    responses={
        401: {"model": ErrorOut, "description": "Unauthorized"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
        404: {"model": ErrorOut, "description": "Recipe not found"},
    },
)
def update_one_recipe(
    recipe_id: int,
    data: RecipeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = get_recipe(db, recipe_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recipe not found")

    _ensure_can_edit(db, current_user.id, rec.family_id, rec.created_by_user_id)

    rec = update_recipe(
        db,
        rec,
        title=data.title,
        description=data.description,
        instructions=data.instructions,
        servings=data.servings,
    )
    return rec


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorOut, "description": "Unauthorized"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
        404: {"model": ErrorOut, "description": "Recipe not found"},
    },
)
def delete_one_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = get_recipe(db, recipe_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recipe not found")

    _ensure_can_edit(db, current_user.id, rec.family_id, rec.created_by_user_id)

    delete_recipe(db, rec)
    return None