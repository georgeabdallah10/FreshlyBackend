# crud/diet_tags.py
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.diet_tag import DietTag


def list_diet_tags(db: Session) -> list[DietTag]:
    return db.query(DietTag).order_by(DietTag.name.asc()).all()


def get_diet_tag(db: Session, tag_id: int) -> DietTag | None:
    return db.query(DietTag).filter(DietTag.id == tag_id).first()


def get_diet_tag_by_name(db: Session, name: str) -> DietTag | None:
    return db.query(DietTag).filter(DietTag.name == name).first()


def create_diet_tag(db: Session, *, name: str) -> DietTag:
    tag = DietTag(name=name)
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(tag)
    return tag


def update_diet_tag(db: Session, tag: DietTag, *, name: str) -> DietTag:
    tag.name = name
    db.add(tag)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(tag)
    return tag


def delete_diet_tag(db: Session, tag: DietTag) -> None:
    db.delete(tag)
    db.commit()