# routers/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user
from models.user import User
from schemas.user import UserOut
from pydantic import BaseModel

# Shared error schema for consistent error responses
class ErrorOut(BaseModel):
    detail: str

router = APIRouter(prefix="/users", tags=["users"])

class UserUpdate(BaseModel):
    name: str | None = None

@router.get("/me", response_model=UserOut, responses={401: {"model": ErrorOut, "description": "Unauthorized"}})
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=UserOut, responses={
    401: {"model": ErrorOut, "description": "Unauthorized"},
    404: {"model": ErrorOut, "description": "User not found"}
})
def update_me(data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if data.name is not None:
        current_user.name = data.name
    db.add(current_user); db.commit(); db.refresh(current_user)
    return current_user