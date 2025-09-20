# crud/user_preferences.py
from sqlalchemy.orm import Session
from models.user_preference import UserPreference


def get_user_preference(db: Session, user_id: int) -> UserPreference | None:
    """Return preferences for a user (or None)."""
    return db.query(UserPreference).filter(UserPreference.user_id == user_id).first()


def create_or_update_user_preference(
    db: Session,
    user_id: int,
    *,
    diet_codes: list[str] | None = None,
    allergen_ingredient_ids: list[int] | None = None,
    disliked_ingredient_ids: list[int] | None = None,
    goal: str | None = None,
    calorie_target: int | None = None,
) -> UserPreference:
    pref = get_user_preference(db, user_id)
    if pref:
        if diet_codes is not None:
            pref.diet_codes = diet_codes
        if allergen_ingredient_ids is not None:
            pref.allergen_ingredient_ids = allergen_ingredient_ids
        if disliked_ingredient_ids is not None:
            pref.disliked_ingredient_ids = disliked_ingredient_ids
        if goal is not None:
            pref.goal = goal
        if calorie_target is not None:
            pref.calorie_target = calorie_target
    else:
        pref = UserPreference(
            user_id=user_id,
            diet_codes=diet_codes,
            allergen_ingredient_ids=allergen_ingredient_ids,
            disliked_ingredient_ids=disliked_ingredient_ids,
            goal=goal,
            calorie_target=calorie_target,
        )
        db.add(pref)

    db.commit()
    db.refresh(pref)
    return pref


def delete_user_preference(db: Session, pref: UserPreference) -> None:
    db.delete(pref)
    db.commit()