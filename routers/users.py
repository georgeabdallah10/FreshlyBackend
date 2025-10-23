# routers/users.py
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user
from models.user import User
from schemas.user import UserOut, UserUpdate
from crud.users import update_user_info, delete_user
from pydantic import BaseModel

# Shared error schema for consistent error responses
class ErrorOut(BaseModel):
    detail: str

router = APIRouter(prefix="/users", tags=["users"])

@router.get(
    "/me",
    response_model=UserOut,
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}}
)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the current logged-in user."""
    return current_user


@router.patch(
    "/me",
    response_model=UserOut,
    responses={
        401: {"model": ErrorOut, "description": "Unauthorized"},
        404: {"model": ErrorOut, "description": "User not found"}
    }
)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update the current user's profile fields (name, email, phone_number)."""
    # Only send changed, non-null fields to the CRUD layer
    update_data = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if update_data:
        current_user = update_user_info(db, current_user, **update_data)
    return current_user


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}}
)
def delete_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete the current user's account."""
    delete_user(db, current_user)
    # 204 No Content
    return Response(status_code=status.HTTP_204_NO_CONTENT)