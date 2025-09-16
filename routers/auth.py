from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db
from core.security import hash_password, verify_password, create_access_token
from models.user import User
from schemas.auth import RegisterIn, LoginIn, TokenOut
from schemas.user import UserOut
from core.deps import get_current_user
from pydantic import BaseModel


class ErrorOut(BaseModel):
    detail: str

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, responses={400: {"model": ErrorOut, "description": "Email already registered"}})
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    u = User(email=data.email, name=data.name, hashed_password=hash_password(data.password))
    db.add(u); db.commit(); db.refresh(u)
    return u

@router.post("/login", response_model=TokenOut, responses={400: {"model": ErrorOut, "description": "Invalid credentials"}})
def login(data: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == data.email).first()
    if not u or not verify_password(data.password, u.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    return TokenOut(access_token=create_access_token(sub=str(u.id)))

@router.get("/me", response_model=UserOut, responses={401: {"model": ErrorOut, "description": "Unauthorized"}})
def me(current_user: User = Depends(get_current_user)):
    return current_user