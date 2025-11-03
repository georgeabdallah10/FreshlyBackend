# crud/families.py
import secrets
from sqlalchemy.orm import Session, joinedload
from models.family import Family
from models.membership import FamilyMembership
from models.user import User


def _new_invite_code() -> str:
    return secrets.token_urlsafe(6)


def create_family(db: Session, display_name: str, owner: User) -> Family:
    fam = Family(display_name=display_name, invite_code=_new_invite_code())
    db.add(fam)
    db.flush()
    db.add(FamilyMembership(family_id=fam.id, user_id=owner.id, role="owner"))
    db.commit()
    db.refresh(fam)
    return fam


def list_user_families(db: Session, user: User) -> list[Family]:
    return (
        db.query(Family)
        .join(FamilyMembership, FamilyMembership.family_id == Family.id)
        .filter(FamilyMembership.user_id == user.id)
        .all()
    )


def join_family_by_code(db: Session, user: User, invite_code: str) -> FamilyMembership | None:
    fam = db.query(Family).filter(Family.invite_code == invite_code).first()
    if not fam:
        return None

    m = db.query(FamilyMembership).filter_by(family_id=fam.id, user_id=user.id).first()
    if m:
        return m

    m = FamilyMembership(family_id=fam.id, user_id=user.id, role="member")
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def list_members(db: Session, family_id: int) -> list[FamilyMembership]:
    """
    Get all members of a family with their user data eagerly loaded.
    Returns memberships with nested user objects for proper frontend display.
    """
    return (
        db.query(FamilyMembership)
        .options(joinedload(FamilyMembership.user))
        .filter(FamilyMembership.family_id == family_id)
        .all()
    )


def remove_member(db: Session, family_id: int, user_id: int) -> bool:
    m = db.query(FamilyMembership).filter_by(family_id=family_id, user_id=user_id).first()
    if not m:
        return False
    db.delete(m)
    db.commit()
    return True


def regenerate_invite_code(db: Session, family_id: int) -> Family | None:
    fam = db.query(Family).get(family_id)
    if not fam:
        return None
    fam.invite_code = _new_invite_code()
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return fam


def delete_family(db: Session, family_id: int) -> bool:
    fam = db.query(Family).get(family_id)
    if not fam:
        return False
    db.delete(fam)  # memberships cascade via FK
    db.commit()
    return True