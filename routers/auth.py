# routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session, selectinload
from pydantic import BaseModel, EmailStr

from core.db import get_db
from core.deps import get_current_user
from core.security import create_access_token, hash_password,decode_token

from models.user import User
from schemas.auth import RegisterIn, LoginIn, TokenOut, OAuthSignupOut
from schemas.user import UserOut
from schemas.user_preference import UserPreferenceCreate

from crud.auth import get_user_by_email, create_user, authenticate_user
from crud.user_preferences import create_user_preference

import random
from fastapi import APIRouter, HTTPException
from core.email_utils import send_verification_email, send_password_reset_code
from datetime import datetime, timedelta, timezone
from services.oauth_signup import OAuthSignupService


class ErrorOut(BaseModel):
    detail: str
    
class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str


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
    user = create_user(db, email=data.email, name=data.name, password=data.password, phone_number=data.phone_number)
    if getattr(data, "preference", None) is not None:
        # create a UserPreference row tied to this new user
        create_user_preference(
            db,
            user_id=user.id,
    diet_codes=data.preference.diet_codes if data.preference else None,
    allergen_ingredient_ids=data.preference.allergen_ingredient_ids if data.preference else None,
    disliked_ingredient_ids=data.preference.disliked_ingredient_ids if data.preference else None,
    goal=(data.preference.goal if data.preference else None),
    calorie_target=(data.preference.calorie_target if data.preference else None),        )
    else:
        create_user_preference(
            db,
            user_id=user.id,
            allergen_ingredient_ids=[],
            diet_codes=[],
            disliked_ingredient_ids=[],
            goal="balanced",
            calorie_target=2000
        )
    # reload with relationships eagerly loaded for response
    user = (
        db.query(User)
        .options(selectinload(User.preference))
        .filter(User.id == user.id)
        .first()
    )
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
    # TEMPORARILY SKIP EMAIL VERIFICATION
    # If you want to enforce verification, uncomment below:
    # if not user.is_verified:
    #     raise HTTPException(status_code=403, detail="Please verify your email before logging in.")
    # issue JWT
    return TokenOut(access_token=create_access_token(sub=str(user.id)))


@router.post(
    "/signup/oauth",
    response_model=OAuthSignupOut,
    responses={
        401: {"model": ErrorOut, "description": "Invalid or expired token"},
        409: {"model": ErrorOut, "description": "User already exists"},
    },
)
async def signup_oauth(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    """Register a new user using a Supabase-issued OAuth token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    supabase_token = authorization.split(" ", 1)[1].strip()
    if not supabase_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user, provider, username = await OAuthSignupService.register(db, supabase_token)
    access_token = OAuthSignupService.issue_access_token(user)

    return OAuthSignupOut(
        access_token=access_token,
        user={
            "id": user.id,
            "email": user.email,
            "username": username,
            "auth_provider": provider,
        },
    )


@router.get(
    "/me",
    response_model=UserOut,
    responses={401: {"model": ErrorOut, "description": "Unauthorized"}},
)
def me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Re-query to ensure relationships are loaded for the response model
    user = (
        db.query(User)
        .options(selectinload(User.preference))
        .filter(User.id == current_user.id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

class SendCodeIn(BaseModel):
    email: EmailStr

@router.post("/send-code")
async def send_code(payload: SendCodeIn, db: Session = Depends(get_db)):
    user = get_user_by_email(db, email=payload.email)
    if not user:
        # optional: avoid leaking which emails exist
        raise HTTPException(status_code=404, detail="Account not found")

    # throttle: don’t blast email every millisecond
    now = datetime.now(timezone.utc)
    if user.verification_expires_at and user.verification_expires_at > now:
        # allow re-send but keep the same code within the window
        code = user.verification_code
    else:
        # generate a fresh 6-digit code valid for 10 minutes
        code = f"{random.randint(100000, 999999)}"
        user.verification_code = code
        user.verification_expires_at = now + timedelta(minutes=10)
        db.add(user)
        db.commit()
        db.refresh(user)

    # await send_verification_email(payload.email, code)  # disabled for now
    return {"message": "Verification code sent."}

@router.post("/verify-code")
def verify_code(payload: VerifyCodeIn, db: Session = Depends(get_db)):
    user: User = get_user_by_email(db, email=payload.email)     
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    now = datetime.now(timezone.utc)
    if not user.verification_code or not user.verification_expires_at:
        raise HTTPException(status_code=400, detail="No active verification code.")
    if user.verification_expires_at < now:
        # clear expired code
        user.verification_code = None
        user.verification_expires_at = None
        db.add(user); db.commit()
        raise HTTPException(status_code=400, detail="Verification code expired.")
    if payload.code.strip() != user.verification_code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    # success → mark verified and clear code
    # user.is_verified = True  # skipping verification update for now
    user.verification_code = None
    user.verification_expires_at = None
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Email verified successfully.", "is_verified": user.is_verified}

class ForgotPasswordIn(BaseModel):
    email: EmailStr

class VerifyResetCodeIn(BaseModel):
    email: EmailStr
    code: str  # keep as string (leading zeros)

class ResetPasswordIn(BaseModel):
    reset_token: str
    new_password: str
    
# ---------- 1) Request reset: send code ----------
@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)):
    user: User | None = get_user_by_email(db, email=payload.email)
    # Optional: avoid leaking existence; return 200 regardless.
    if not user:
        return {"message": "If that account exists, a reset code was sent."}

    now = datetime.now(timezone.utc)

    # throttle: allow resend but limit frequency via expiry window
    if user.password_reset_expires_at and user.password_reset_expires_at > now:
        code = user.password_reset_code
    else:
        code = f"{random.randint(100000, 999999)}"
        user.password_reset_code = code
        user.password_reset_expires_at = now + timedelta(minutes=10)
        user.password_reset_attempts = 0
        db.add(user); db.commit(); db.refresh(user)

    await send_password_reset_code(user.email, code)
    return {"message": "If that account exists, a reset code was sent."}

# ---------- 2) Verify code -> issue one-time short-lived reset token ----------
@router.post("/forgot-password/verify")
def verify_reset_code(payload: VerifyResetCodeIn, db: Session = Depends(get_db)):
    user: User | None = get_user_by_email(db, email=payload.email)
    if not user or not user.password_reset_code or not user.password_reset_expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired code.")

    now = datetime.now(timezone.utc)
    if user.password_reset_expires_at < now:
        # clear stale state
        user.password_reset_code = None
        user.password_reset_expires_at = None
        db.add(user); db.commit()
        raise HTTPException(status_code=400, detail="Code expired. Request a new one.")

    # small brute-force protection
    if user.password_reset_attempts >= 5:
        raise HTTPException(status_code=429, detail="Too many attempts. Request a new code.")
    if payload.code.strip() != user.password_reset_code:
        user.password_reset_attempts += 1
        db.add(user); db.commit()
        raise HTTPException(status_code=400, detail="Invalid code.")

    # success -> issue short-lived reset token (e.g., 15 minutes)

    reset_token = create_access_token(
    sub=str(user.id),
    extra={
        "scope": "password_reset",
        # override default expiry with a short-lived 15-min token
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    },
)
    # clear the code so it’s one-time
    user.password_reset_code = None
    user.password_reset_expires_at = None
    user.password_reset_attempts = 0
    db.add(user); db.commit()

    return {"message": "Code verified.", "reset_token": reset_token}

# ---------- 3) Reset password with token ----------
@router.post("/reset-password")
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    # 1) Decode and validate token
    try:
        claims = decode_token(payload.reset_token)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired token.")

    # 2) Check scope
    if claims.get("scope") != "password_reset":
        raise HTTPException(status_code=403, detail="Invalid token scope.")

    # 3) Load user
    user_id = int(claims["sub"])
    user: User | None = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # 4) Validate new password
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    # 5) Update password + clear reset state
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_code = None
    user.password_reset_expires_at = None
    user.password_reset_attempts = 0

    db.add(user)
    db.commit()

    return {"message": "Password has been reset successfully."}
