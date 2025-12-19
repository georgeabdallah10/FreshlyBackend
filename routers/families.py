# routers/families.py
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user, require_family_role
from models.user import User
from models.membership import FamilyMembership
from schemas.family import FamilyCreate, FamilyOut, JoinByCodeIn
from schemas.membership import MembershipOut, MembershipRoleUpdate
from schemas.meal import MealOut
from schemas.user_preference import UserPreferenceOut
from schemas.user import UserOut
from pydantic import BaseModel
from typing import Optional

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
from crud.meals import list_user_all_meals

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
    current_user: User = Depends(get_current_user),
):
    membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.family_id == family_id,
            FamilyMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")

    # Self-leave is always allowed, no role check needed
    if membership.user_id == current_user.id:
        crud_remove_member(db, family_id, user_id)
        return {"ok": True}

    # Removing someone else requires admin/owner membership in this family
    actor_membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.family_id == family_id,
            FamilyMembership.user_id == current_user.id,
        )
        .first()
    )
    if not actor_membership or actor_membership.role not in ("admin", "owner"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if membership.role == "owner":
        owner_count = (
            db.query(FamilyMembership)
            .filter(
                FamilyMembership.family_id == family_id,
                FamilyMembership.role == "owner",
            )
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Family must retain at least one owner",
            )

    crud_remove_member(db, family_id, user_id)
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


@router.patch(
    "/{family_id}/members/{user_id}/role",
    response_model=MembershipOut,
    responses={
        400: {"model": ErrorOut, "description": "Invalid role transition"},
        404: {"model": ErrorOut, "description": "Not a member"},
        403: {"model": ErrorOut, "description": "Insufficient permissions"},
    },
)
def update_member_role(
    family_id: int,
    user_id: int,
    data: MembershipRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_family_role("admin")),
):
    membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.family_id == family_id,
            FamilyMembership.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")

    if membership.role == data.role:
        return membership

    actor_membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.family_id == family_id,
            FamilyMembership.user_id == current_user.id,
        )
        .first()
    )
    if not actor_membership:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    if actor_membership.role == "admin":
        if membership.role == "owner" or data.role == "owner":
            raise HTTPException(
                status_code=403,
                detail="Admins cannot modify owners or assign owner role",
            )

    if membership.role == "owner" and data.role != "owner":
        owner_count = (
            db.query(FamilyMembership)
            .filter(
                FamilyMembership.family_id == family_id,
                FamilyMembership.role == "owner",
            )
            .count()
        )
        if owner_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Family must retain at least one owner",
            )

    membership.role = data.role
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


# Family Owner Dashboard Endpoints - Read-only access to member data
@router.get(
    "/{family_id}/members/{user_id}/meals",
    response_model=list[MealOut],
    responses={
        403: {"model": ErrorOut, "description": "Only family owners can access this endpoint"},
        404: {"model": ErrorOut, "description": "User is not a member of this family"},
    },
)
def get_member_meals(
    family_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("owner")),
):
    """
    Get all meals created by a specific family member (read-only).
    Only family owners can access this endpoint.
    """
    # Verify the user is a member of this family
    membership = db.query(FamilyMembership).filter(
        FamilyMembership.family_id == family_id,
        FamilyMembership.user_id == user_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this family")
    
    return list_user_all_meals(db, user_id)


@router.get(
    "/{family_id}/members/{user_id}/preferences",
    response_model=UserPreferenceOut,
    responses={
        403: {"model": ErrorOut, "description": "Only family owners can access this endpoint"},
        404: {"model": ErrorOut, "description": "User preferences not found or user is not a member"},
    },
)
def get_member_preferences(
    family_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("owner")),
):
    """
    Get preferences for a specific family member (read-only).
    Only family owners can access this endpoint.
    """
    from models.user_preference import UserPreference
    
    # Verify the user is a member of this family
    membership = db.query(FamilyMembership).filter(
        FamilyMembership.family_id == family_id,
        FamilyMembership.user_id == user_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this family")
    
    # Get user preferences
    preferences = db.query(UserPreference).filter(
        UserPreference.user_id == user_id
    ).first()
    
    if not preferences:
        raise HTTPException(status_code=404, detail="User preferences not found")
    
    return preferences


@router.get(
    "/{family_id}/members/{user_id}/profile",
    response_model=UserOut,
    responses={
        403: {"model": ErrorOut, "description": "Only family owners can access this endpoint"},
        404: {"model": ErrorOut, "description": "User not found or not a member of this family"},
    },
)
def get_member_profile(
    family_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_family_role("owner")),
):
    """
    Get profile information for a specific family member (read-only).
    Only family owners can access this endpoint.
    """
    # Verify the user is a member of this family
    membership = db.query(FamilyMembership).filter(
        FamilyMembership.family_id == family_id,
        FamilyMembership.user_id == user_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of this family")
    
    # Get the user
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user
