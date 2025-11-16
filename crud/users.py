# crud/users.py
from sqlalchemy.orm import Session
from models.user import User



def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Fetch a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def update_user_info(db: Session, user: User, name: str | None = None, **fields) -> User:
    # Allowlist of columns that can be updated via this helper
    allowed_fields = {"name", "email", "phone_number", "location", "avatar_path", "age", "weight", "height"}
    changed = False

    # Collect updates: include `name` if provided, then any extra kwargs
    updates = {}
    if name is not None:
        updates["name"] = name
    for key, value in fields.items():
        if value is not None and key in allowed_fields:
            updates[key] = value

    if not updates:
        return user  # nothing to change

    # Apply updates
    for key, value in updates.items():
        setattr(user, key, value)
        changed = True
    if changed:
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Permanently delete a user."""
    db.delete(user)
    db.commit()
