import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user, require_family_role
from models.family import Family
from models.membership import FamilyMembership
from models.user import User
from schemas.family import FamilyCreate, FamilyOut, JoinByCodeIn
from schemas.membership import MembershipOut
from fastapi import Path

from pydantic import BaseModel


class ErrorOut(BaseModel):
    detail: str


router = APIRouter(prefix="/families", tags=["families"])

def _new_invite_code() -> str:
    return secrets.token_urlsafe(6)

@router.post("", response_model=FamilyOut, responses={401: {"model": ErrorOut, "description": "Unauthorized"}})
def create_family(data: FamilyCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fam = Family(display_name=data.display_name, invite_code=_new_invite_code())
    db.add(fam); db.flush()
    db.add(FamilyMembership(family_id=fam.id, user_id=user.id, role="owner"))
    db.commit(); db.refresh(fam)
    return fam

@router.get("", response_model=list[FamilyOut], responses={401: {"model": ErrorOut, "description": "Unauthorized"}})
def list_my_families(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Family)
        .join(FamilyMembership, FamilyMembership.family_id == Family.id)
        .filter(FamilyMembership.user_id == user.id)
        .all()
    )

@router.post("/join", response_model=MembershipOut, responses={404: {"model": ErrorOut, "description": "Invalid invite code"}})
def join_by_code(data: JoinByCodeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    fam = db.query(Family).filter(Family.invite_code == data.invite_code).first()
    if not fam: raise HTTPException(status_code=404, detail="Invalid invite code")
    m = db.query(FamilyMembership).filter_by(family_id=fam.id, user_id=user.id).first()
    if m: return m
    m = FamilyMembership(family_id=fam.id, user_id=user.id, role="member")
    db.add(m); db.commit(); db.refresh(m)
    return m

@router.get("/{family_id}/members", response_model=list[MembershipOut], responses={403: {"model": ErrorOut, "description": "Insufficient permissions"}})
def list_members(family_id: int, db: Session = Depends(get_db), user: User = Depends(require_family_role("member"))):
    return db.query(FamilyMembership).filter(FamilyMembership.family_id == family_id).all()

@router.delete("/{family_id}/members/{user_id}", responses={404: {"model": ErrorOut, "description": "Not a member"}, 403: {"model": ErrorOut, "description": "Insufficient permissions"}})
def remove_member(family_id: int, user_id: int, db: Session = Depends(get_db), _: User = Depends(require_family_role("admin"))):
    m = db.query(FamilyMembership).filter_by(family_id=family_id, user_id=user_id).first()
    if not m: raise HTTPException(status_code=404, detail="Not a member")
    db.delete(m); db.commit()
    return {"ok": True}

@router.post("/{family_id}/invite/regenerate", response_model=FamilyOut, responses={404: {"model": ErrorOut, "description": "Family not found"}, 403: {"model": ErrorOut, "description": "Insufficient permissions"}})
def regenerate_invite(
    family_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("admin")),
):
    fam = db.query(Family).get(family_id)
    if not fam: raise HTTPException(status_code=404, detail="Family not found")
    fam.invite_code = _new_invite_code()
    db.add(fam); db.commit(); db.refresh(fam)
    return fam

@router.delete("/{family_id}", responses={404: {"model": ErrorOut, "description": "Family not found"}, 403: {"model": ErrorOut, "description": "Insufficient permissions"}})
def delete_family(
    family_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("owner")),
):
    fam = db.query(Family).get(family_id)
    if not fam: raise HTTPException(status_code=404, detail="Family not found")
    db.delete(fam)          # memberships cascade via FK
    db.commit()
    return {"ok": True}