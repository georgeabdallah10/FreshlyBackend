# routers/memberships.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user, require_family_role
from models.user import User
from pydantic import BaseModel

# CRUD layer
from crud.memberships import (
    get_membership,
    update_membership_role,
    delete_membership,
)

class ErrorOut(BaseModel):
    detail: str

router = APIRouter(prefix="/memberships", tags=["memberships"])

class RoleUpdate(BaseModel):
    role: str  # 'member' | 'admin' | 'owner'


@router.patch(
    "/{membership_id}/role",
    responses={
        400: {"model": ErrorOut, "description": "Invalid role"},
        401: {"model": ErrorOut, "description": "Unauthorized"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
        404: {"model": ErrorOut, "description": "Membership not found"},
    },
)
def update_role(
    membership_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("owner")),  # only owner can change roles
):
    if data.role not in ("member", "admin", "owner"):
        raise HTTPException(status_code=400, detail="Invalid role")

    m = get_membership(db, membership_id)
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")

    m = update_membership_role(db, m, data.role)
    return {"ok": True}


@router.delete(
    "/{membership_id}",
    responses={
        401: {"model": ErrorOut, "description": "Unauthorized"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
        404: {"model": ErrorOut, "description": "Membership not found"},
    },
)
def leave_or_kick(
    membership_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = get_membership(db, membership_id)
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")

    # Allow self-leave OR admins/owners kicking others in same family
    if m.user_id == current_user.id:
        delete_membership(db, m)
        return {"ok": True, "left": True}

    # Check authority in the same family (admin or owner)
    from core.deps import require_family_role as _guard
    _guard("admin")(m.family_id, current_user, db)  # raises if insufficient

    delete_membership(db, m)
    return {"ok": True, "kicked": True}