# crud/user_preferences.py
from sqlalchemy.orm import Session
from models.user_preference import UserPreference


def get_user_preference(db: Session, user_id: int) -> UserPreference | None:
    """Return preferences for a user (or None)."""
    return db.query(UserPreference).filter(UserPreference.user_id == user_id).first()


def create_user_preference(
    db: Session,
    user_id: int,
    *,
    # Basic body information
    age: int | None = None,
    gender: str | None = None,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    # Dietary preferences (legacy)
    diet_codes: list[str] | None = None,
    allergen_ingredient_ids: list[int] | None = None,
    disliked_ingredient_ids: list[int] | None = None,
    # Dietary preferences (new)
    diet_type: str | None = None,
    food_allergies: list[str] | None = None,
    # Goal & athlete
    goal: str = "balanced",
    is_athlete: bool = False,
    training_level: str | None = None,
    # Nutrition targets
    calorie_target: int = 2000,
    protein_grams: float | None = None,
    carb_grams: float | None = None,
    fat_grams: float | None = None,
    protein_calories: float | None = None,
    carb_calories: float | None = None,
    fat_calories: float | None = None,
    # Safety range
    calorie_min: int | None = None,
    calorie_max: int | None = None,
) -> UserPreference:
    """Create a new user preference record."""
    return create_or_update_user_preference(
        db,
        user_id,
        age=age,
        gender=gender,
        height_cm=height_cm,
        weight_kg=weight_kg,
        diet_codes=diet_codes,
        allergen_ingredient_ids=allergen_ingredient_ids,
        disliked_ingredient_ids=disliked_ingredient_ids,
        diet_type=diet_type,
        food_allergies=food_allergies,
        goal=goal,
        calorie_target=calorie_target,
        is_athlete=is_athlete,
        training_level=training_level,
        protein_grams=protein_grams,
        carb_grams=carb_grams,
        fat_grams=fat_grams,
        protein_calories=protein_calories,
        carb_calories=carb_calories,
        fat_calories=fat_calories,
        calorie_min=calorie_min,
        calorie_max=calorie_max,
    )


def create_or_update_user_preference(
    db: Session,
    user_id: int,
    *,
    # Basic body information
    age: int | None = None,
    gender: str | None = None,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    # Dietary preferences (legacy)
    diet_codes: list[str] | None = None,
    allergen_ingredient_ids: list[int] | None = None,
    disliked_ingredient_ids: list[int] | None = None,
    # Dietary preferences (new)
    diet_type: str | None = None,
    food_allergies: list[str] | None = None,
    # Goal & athlete
    goal: str | None = None,
    is_athlete: bool | None = None,
    training_level: str | None = None,
    # Nutrition targets
    calorie_target: int | None = None,
    protein_grams: float | None = None,
    carb_grams: float | None = None,
    fat_grams: float | None = None,
    protein_calories: float | None = None,
    carb_calories: float | None = None,
    fat_calories: float | None = None,
    # Safety range
    calorie_min: int | None = None,
    calorie_max: int | None = None,
) -> UserPreference:
    """Create or update user preferences with partial update support."""
    pref = get_user_preference(db, user_id)

    if pref:
        # Update existing preference
        # Basic body information
        if age is not None:
            pref.age = age
        if gender is not None:
            pref.gender = gender
        if height_cm is not None:
            pref.height_cm = height_cm
        if weight_kg is not None:
            pref.weight_kg = weight_kg

        # Dietary preferences (legacy)
        if diet_codes is not None:
            pref.diet_codes = diet_codes
        if allergen_ingredient_ids is not None:
            pref.allergen_ingredient_ids = allergen_ingredient_ids
        if disliked_ingredient_ids is not None:
            pref.disliked_ingredient_ids = disliked_ingredient_ids

        # Dietary preferences (new)
        if diet_type is not None:
            pref.diet_type = diet_type
        if food_allergies is not None:
            pref.food_allergies = food_allergies

        # Goal
        if goal is not None:
            pref.goal = goal

        # Nutrition targets
        if calorie_target is not None:
            pref.calorie_target = calorie_target
        if protein_grams is not None:
            pref.protein_grams = protein_grams
        if carb_grams is not None:
            pref.carb_grams = carb_grams
        if fat_grams is not None:
            pref.fat_grams = fat_grams
        if protein_calories is not None:
            pref.protein_calories = protein_calories
        if carb_calories is not None:
            pref.carb_calories = carb_calories
        if fat_calories is not None:
            pref.fat_calories = fat_calories

        # Safety range
        if calorie_min is not None:
            pref.calorie_min = calorie_min
        if calorie_max is not None:
            pref.calorie_max = calorie_max

        # Athlete mode handling
        if is_athlete is not None:
            pref.is_athlete = is_athlete
        if training_level is not None:
            pref.training_level = training_level

        # Enforce athlete/training_level constraints
        final_is_athlete = pref.is_athlete
        if final_is_athlete is False:
            pref.training_level = None
        elif pref.training_level is None:
            raise ValueError("training_level is required when is_athlete is true")

    else:
        # Create new preference
        if is_athlete is True and training_level is None:
            raise ValueError("training_level is required when is_athlete is true")

        pref = UserPreference(
            user_id=user_id,
            # Basic body information
            age=age,
            gender=gender,
            height_cm=height_cm,
            weight_kg=weight_kg,
            # Dietary preferences (legacy)
            diet_codes=diet_codes if diet_codes is not None else [],
            allergen_ingredient_ids=allergen_ingredient_ids if allergen_ingredient_ids is not None else [],
            disliked_ingredient_ids=disliked_ingredient_ids if disliked_ingredient_ids is not None else [],
            # Dietary preferences (new)
            diet_type=diet_type,
            food_allergies=food_allergies if food_allergies is not None else [],
            # Goal & athlete
            goal=goal if goal is not None else "balanced",
            is_athlete=is_athlete if is_athlete is not None else False,
            training_level=training_level,
            # Nutrition targets
            calorie_target=calorie_target if calorie_target is not None else 2000,
            protein_grams=protein_grams,
            carb_grams=carb_grams,
            fat_grams=fat_grams,
            protein_calories=protein_calories,
            carb_calories=carb_calories,
            fat_calories=fat_calories,
            # Safety range
            calorie_min=calorie_min,
            calorie_max=calorie_max,
        )

        # Enforce athlete/training_level constraints
        if pref.is_athlete is False:
            pref.training_level = None
        elif pref.training_level is None:
            raise ValueError("training_level is required when is_athlete is true")

        db.add(pref)

    db.commit()
    db.refresh(pref)
    return pref


def delete_user_preference(db: Session, pref: UserPreference) -> None:
    """Delete a user preference record."""
    db.delete(pref)
    db.commit()
