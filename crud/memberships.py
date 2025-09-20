# crud/memberships.py
from sqlalchemy.orm import Session
from models.membership import FamilyMembership


def get_membership(db: Session, membership_id: int) -> FamilyMembership | None:
    """Fetch a membership by ID."""
    return db.query(FamilyMembership).get(membership_id)


def update_membership_role(
    db: Session, membership: FamilyMembership, role: str
) -> FamilyMembership:
    """Update the role on a family membership and persist."""
    membership.role = role
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def delete_membership(db: Session, membership: FamilyMembership) -> None:
    """Delete a membership from the database."""
    db.delete(membership)
    db.commit()