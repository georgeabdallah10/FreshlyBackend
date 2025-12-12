# crud/user_preferences.py
from sqlalchemy.orm import Session
from models.user_preference import UserPreference


# Alias for backward compatibility/imports in routers/auth.py
def create_user_preference(
    db: Session,
    user_id: int,
    *,
    diet_codes: list[str],
    allergen_ingredient_ids: list[int] ,
    disliked_ingredient_ids: list[int],
    goal: str,
    calorie_target: int ,
    is_athlete: bool = False,
    training_level: str | None = None,
) -> UserPreference:
    return create_or_update_user_preference(
        db,
        user_id,
        diet_codes=diet_codes,
        allergen_ingredient_ids=allergen_ingredient_ids,
        disliked_ingredient_ids=disliked_ingredient_ids,
        goal=goal,
        calorie_target=calorie_target,
        is_athlete=is_athlete,
        training_level=training_level,
    )


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
    is_athlete: bool | None = None,
    training_level: str | None = None,
) -> UserPreference:
    pref = get_user_preference(db, user_id)
    if pref:
        if is_athlete is True and training_level is None:
            raise ValueError("training_level is required when is_athlete is true")
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
        if is_athlete is not None:
            pref.is_athlete = is_athlete
        if training_level is not None:
            pref.training_level = training_level

        final_is_athlete = pref.is_athlete
        if final_is_athlete is False:
            pref.training_level = None
        elif pref.training_level is None:
            # is_athlete True but training not provided -> reject
            raise ValueError("training_level is required when is_athlete is true")
    else:
        if is_athlete is True and training_level is None:
            raise ValueError("training_level is required when is_athlete is true")
        pref = UserPreference(
            user_id=user_id,
            diet_codes=diet_codes,
            allergen_ingredient_ids=allergen_ingredient_ids,
            disliked_ingredient_ids=disliked_ingredient_ids,
            goal=goal,
            calorie_target=calorie_target,
            is_athlete=is_athlete if is_athlete is not None else False,
            training_level=training_level,
        )
        if pref.is_athlete is False:
            pref.training_level = None
        elif pref.training_level is None:
            raise ValueError("training_level is required when is_athlete is true")
        db.add(pref)

    db.commit()
    db.refresh(pref)
    return pref


def delete_user_preference(db: Session, pref: UserPreference) -> None:
    db.delete(pref)
    db.commit()
