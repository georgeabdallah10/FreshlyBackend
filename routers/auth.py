# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.db import get_db
from core.deps import get_current_user
from core.security import create_access_token

from models.user import User
from schemas.auth import RegisterIn, LoginIn, TokenOut
from schemas.user import UserOut

from crud.auth import get_user_by_email, create_user, authenticate_user


class ErrorOut(BaseModel):
    detail: str


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    responses={400: {"model": ErrorOut, "description": "Email already registered"}},
)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    # prevent duplicate emails
    if get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    # create user
    user = create_user(db, email=data.email, name=data.name, password=data.password)
    return user


@router.post(
    "/login",
    response_model=TokenOut,
    responses={400: {"model": ErrorOut, "description": "Invalid credentials"}},
)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = authenticate_user(db, email=data.email, password=data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    # issue JWT
    return TokenOut(access_token=create_access_token(sub=str(user.id)))


@router.get(
    "/me",
    response_model=UserOut,
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}},
)
def me(current_user: User = Depends(get_current_user)):
    return current_user