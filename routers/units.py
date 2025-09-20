# routers/units.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from core.db import get_db
from core.deps import get_current_user  # if you want endpoints protected
from schemas.unit import UnitCreate, UnitOut
from crud.units import list_units, get_unit, get_unit_by_code, create_unit, update_unit, delete_unit

router = APIRouter(prefix="/units", tags=["units"])


class ErrorOut(BaseModel):
    detail: str


class UnitUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=32)
    display_name: str | None = Field(None, max_length=100)
    is_metric: bool | None = None


@router.get(
    "",
    response_model=list[UnitOut],
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}},
)
def list_all_units(
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),  # remove if you want it public
):
    return list_units(db)


@router.get(
    "/{unit_id}",
    response_model=UnitOut,
    responses={404: {"model": ErrorOut, "description": "Unit not found"}},
)
def get_one_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = get_unit(db, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.post(
    "",
    response_model=UnitOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorOut, "description": "Unit code already exists"}},
)
def create_one_unit(
    data: UnitCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),  # protect if needed
):
    # Optional: pre-check to return clean 409 rather than IntegrityError
    if get_unit_by_code(db, data.code):
        raise HTTPException(status_code=409, detail="Unit code already exists")
    try:
        return create_unit(db, code=data.code, display_name=data.display_name, is_metric=data.is_metric)
    except Exception:
        # Unique violation fallback
        raise HTTPException(status_code=409, detail="Unit code already exists")


@router.patch(
    "/{unit_id}",
    response_model=UnitOut,
    responses={
        404: {"model": ErrorOut, "description": "Unit not found"},
        409: {"model": ErrorOut, "description": "Unit code already exists"},
    },
)
def update_one_unit(unit_id: int, data: UnitUpdate, db: Session = Depends(get_db)):
    unit = get_unit(db, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    # If changing code, sanity-check conflict
    if data.code is not None:
        existing = get_unit_by_code(db, data.code)
        if existing and existing.id != unit.id:
            raise HTTPException(status_code=409, detail="Unit code already exists")
    try:
        return update_unit(
            db,
            unit,
            code=data.code,
            display_name=data.display_name,
            is_metric=data.is_metric,
        )
    except Exception:
        raise HTTPException(status_code=409, detail="Unit code already exists")


@router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorOut, "description": "Unit not found"}},
)
def delete_one_unit(unit_id: int, db: Session = Depends(get_db)):
    unit = get_unit(db, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    delete_unit(db, unit)
    return None