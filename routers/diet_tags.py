# routers/diet_tags.py
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from schemas.diet_tag import DietTagCreate, DietTagUpdate, DietTagOut
from crud.diet_tags import (
    list_diet_tags,
    get_diet_tag,
    get_diet_tag_by_name,
    create_diet_tag,
    update_diet_tag,
    delete_diet_tag,
)

router = APIRouter(prefix="/diet-tags", tags=["diet_tags"])


class ErrorOut(BaseModel):
    detail: str


@router.get(
    "",
    response_model=list[DietTagOut],
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}},
)
def list_all_tags(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    return list_diet_tags(db)


@router.get(
    "/{tag_id}",
    response_model=DietTagOut,
    responses={404: {"model": ErrorOut, "description": "Tag not found"}},
)
def get_one_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = get_diet_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post(
    "",
    response_model=DietTagOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorOut, "description": "Tag already exists"}},
)
def create_one_tag(
    data: DietTagCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    if get_diet_tag_by_name(db, data.name):
        raise HTTPException(status_code=409, detail="Tag already exists")
    try:
        return create_diet_tag(db, name=data.name)
    except Exception:
        raise HTTPException(status_code=409, detail="Tag already exists")


@router.patch(
    "/{tag_id}",
    response_model=DietTagOut,
    responses={
        404: {"model": ErrorOut, "description": "Tag not found"},
        409: {"model": ErrorOut, "description": "Tag already exists"},
    },
)
def update_one_tag(tag_id: int, data: DietTagUpdate, db: Session = Depends(get_db)):
    tag = get_diet_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    if get_diet_tag_by_name(db, data.name) and get_diet_tag_by_name(db, data.name).id != tag.id:
        raise HTTPException(status_code=409, detail="Tag already exists")
    try:
        return update_diet_tag(db, tag, name=data.name)
    except Exception:
        raise HTTPException(status_code=409, detail="Tag already exists")


@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorOut, "description": "Tag not found"}},
)
def delete_one_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = get_diet_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    delete_diet_tag(db, tag)
    return None