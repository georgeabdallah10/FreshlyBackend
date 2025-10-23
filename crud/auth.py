# crud/auth.py
from sqlalchemy.orm import Session
from models.user import User
from core.security import hash_password, verify_password


def get_user_by_email(db: Session, email: str) -> User | None:
    """Return a user by email (or None)."""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, *, email: str, name: str | None, password: str, phone_number: str | None = None) -> User:
    """
    Create a new user with a hashed password.
    Assumes the caller already checked for duplicate email.
    """
    user = User(email=email, name=name, hashed_password=hash_password(password), phone_number=phone_number)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    """
    Validate credentials. Returns the user if valid, else None.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user