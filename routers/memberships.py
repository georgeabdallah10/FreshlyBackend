# routers/memberships.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user, require_family_role
from models.membership import FamilyMembership
from models.user import User
from pydantic import BaseModel

class ErrorOut(BaseModel):
    detail: str

router = APIRouter(prefix="/memberships", tags=["memberships"])

class RoleUpdate(BaseModel):
    role: str  # 'member' | 'admin' | 'owner'

@router.patch("/{membership_id}/role", responses={
    400: {"model": ErrorOut, "description": "Invalid role"},
    401: {"model": ErrorOut, "description": "Unauthorized"},
    403: {"model": ErrorOut, "description": "Insufficient permissions"},
    404: {"model": ErrorOut, "description": "Membership not found"}
})
def update_role(
    membership_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("owner"))  # only owner can change roles
):
    if data.role not in ("member", "admin", "owner"):
        raise HTTPException(status_code=400, detail="Invalid role")
    m = db.query(FamilyMembership).get(membership_id)
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")
    m.role = data.role
    db.add(m); db.commit()
    return {"ok": True}

@router.delete("/{membership_id}", responses={
    401: {"model": ErrorOut, "description": "Unauthorized"},
    403: {"model": ErrorOut, "description": "Insufficient permissions"},
    404: {"model": ErrorOut, "description": "Membership not found"}
})
def leave_or_kick(
    membership_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    m = db.query(FamilyMembership).get(membership_id)
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")

    # Allow self-leave OR admins/owners kicking others in same family
    if m.user_id == current_user.id:
        db.delete(m); db.commit()
        return {"ok": True, "left": True}

    # Check authority in the same family
    from core.deps import require_family_role as _guard  # reuse guard
    _guard("admin")(m.family_id, current_user, db)  # raises if insufficient
    db.delete(m); db.commit()
    return {"ok": True, "kicked": True}