# routers/families.py
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user, require_family_role
from models.user import User
from schemas.family import FamilyCreate, FamilyOut, JoinByCodeIn
from schemas.membership import MembershipOut
from pydantic import BaseModel

# CRUD
from crud.families import (
    create_family as crud_create_family,
    list_user_families,
    join_family_by_code,
    list_members as crud_list_members,
    remove_member as crud_remove_member,
    regenerate_invite_code,
    delete_family as crud_delete_family,
)

class ErrorOut(BaseModel):
    detail: str

router = APIRouter(prefix="/families", tags=["families"])


@router.post(
    "",
    response_model=FamilyOut,
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}}
)
def create_family(
    data: FamilyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return crud_create_family(db, data.display_name, user)


@router.get(
    "",
    response_model=list[FamilyOut],
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}}
)
def list_my_families(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list_user_families(db, user)


@router.post(
    "/join",
    response_model=MembershipOut,
    responses={404: {"model": ErrorOut, "description": "Invalid invite code"}}
)
def join_by_code(
    data: JoinByCodeIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = join_family_by_code(db, user, data.invite_code)
    if not m:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    return m


@router.get(
    "/{family_id}/members",
    response_model=list[MembershipOut],
    responses={403: {"model": ErrorOut, "description": "Insufficient permissions"}}
)
def list_members(
    family_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("member")),
):
    return crud_list_members(db, family_id)


@router.delete(
    "/{family_id}/members/{user_id}",
    responses={
        404: {"model": ErrorOut, "description": "Not a member"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
    },
)
def remove_member(
    family_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("admin")),
):
    ok = crud_remove_member(db, family_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Not a member")
    return {"ok": True}


@router.post(
    "/{family_id}/invite/regenerate",
    response_model=FamilyOut,
    responses={
        404: {"model": ErrorOut, "description": "Family not found"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
    },
)
def regenerate_invite(
    family_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("admin")),
):
    fam = regenerate_invite_code(db, family_id)
    if not fam:
        raise HTTPException(status_code=404, detail="Family not found")
    return fam


@router.delete(
    "/{family_id}",
    responses={
        404: {"model": ErrorOut, "description": "Family not found"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
    },
)
def delete_family(
    family_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("owner")),
):
    ok = crud_delete_family(db, family_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Family not found")
    return {"ok": True}