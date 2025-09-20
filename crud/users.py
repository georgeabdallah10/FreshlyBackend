# crud/users.py
from sqlalchemy.orm import Session
from models.user import User


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def update_user_name(db: Session, user: User, name: str) -> User:
    """Update a user's name and persist the change."""
    user.name = name
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Permanently delete a user."""
    db.delete(user)
    db.commit()