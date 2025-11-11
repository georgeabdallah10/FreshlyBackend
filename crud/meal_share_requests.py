# crud/meal_share_requests.py
from sqlalchemy.orm import Session
from models.meal_share_request import MealShareRequest
from models.meal import Meal
from schemas.meal_share_request import MealShareRequestCreate
from typing import List, Optional, Tuple
from datetime import datetime
from copy import deepcopy


def create_share_request(
    db: Session,
    data: MealShareRequestCreate,
    sender_user_id: int,
    meal: Meal
) -> MealShareRequest:
    """Create a new meal share request"""
    request = MealShareRequest(
        meal_id=meal.id,
        sender_user_id=sender_user_id,
        recipient_user_id=data.recipient_user_id,
        family_id=meal.family_id,
        message=data.message,
        status="pending"
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_share_request(db: Session, request_id: int) -> Optional[MealShareRequest]:
    """Get a share request by ID"""
    return db.query(MealShareRequest).filter(MealShareRequest.id == request_id).first()


def get_pending_requests_for_user(db: Session, user_id: int) -> List[MealShareRequest]:
    """Get all pending requests sent to a user"""
    return db.query(MealShareRequest).filter(
        MealShareRequest.recipient_user_id == user_id,
        MealShareRequest.status == "pending"
    ).all()


def get_sent_requests(db: Session, sender_user_id: int) -> List[MealShareRequest]:
    """Get all requests sent by a user"""
    return db.query(MealShareRequest).filter(
        MealShareRequest.sender_user_id == sender_user_id
    ).order_by(MealShareRequest.created_at.desc()).all()


def get_received_requests(db: Session, recipient_user_id: int) -> List[MealShareRequest]:
    """Get all requests received by a user"""
    return db.query(MealShareRequest).filter(
        MealShareRequest.recipient_user_id == recipient_user_id
    ).order_by(MealShareRequest.created_at.desc()).all()


def accept_share_request(db: Session, request: MealShareRequest) -> Tuple[MealShareRequest, Meal]:
    """Accept a meal share request and clone the meal for the recipient"""
    meal = request.meal or db.query(Meal).get(request.meal_id)
    if not meal:
        raise ValueError("Original meal not found for this share request.")
    
    cloned_meal = _clone_meal_for_user(db, meal, request.recipient_user_id)
    
    request.status = "accepted"
    request.responded_at = datetime.now()
    request.accepted_meal_id = cloned_meal.id
    db.add(request)
    db.commit()
    db.refresh(request)
    db.refresh(cloned_meal)
    return request, cloned_meal


def decline_share_request(db: Session, request: MealShareRequest) -> MealShareRequest:
    """Decline a meal share request"""
    request.status = "declined"
    request.responded_at = datetime.now()
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def get_accepted_meals_for_user(db: Session, user_id: int) -> List[Meal]:
    """Get all meals that user has accepted from others"""
    accepted_requests = db.query(MealShareRequest).filter(
        MealShareRequest.recipient_user_id == user_id,
        MealShareRequest.status == "accepted",
        MealShareRequest.accepted_meal_id.isnot(None)
    ).all()
    
    meal_ids = [req.accepted_meal_id for req in accepted_requests if req.accepted_meal_id]
    
    if not meal_ids:
        return []
    
    return db.query(Meal).filter(Meal.id.in_(meal_ids)).all()


def check_existing_request(
    db: Session,
    meal_id: int,
    sender_user_id: int,
    recipient_user_id: int
) -> Optional[MealShareRequest]:
    """Check if a request already exists for this meal and recipient"""
    return db.query(MealShareRequest).filter(
        MealShareRequest.meal_id == meal_id,
        MealShareRequest.sender_user_id == sender_user_id,
        MealShareRequest.recipient_user_id == recipient_user_id,
        MealShareRequest.status == "pending"
    ).first()


def delete_share_request(db: Session, request: MealShareRequest):
    """Delete a share request (cancel)"""
    db.delete(request)
    db.commit()


def _clone_meal_for_user(db: Session, meal: Meal, recipient_user_id: int) -> Meal:
    """Create a copy of the meal for the recipient user."""
    cloned_meal = Meal(
        created_by_user_id=recipient_user_id,
        family_id=None,
        name=meal.name,
        image=meal.image,
        calories=meal.calories,
        prep_time=meal.prep_time,
        cook_time=meal.cook_time,
        total_time=meal.total_time,
        meal_type=meal.meal_type,
        cuisine=meal.cuisine,
        tags=deepcopy(meal.tags) if meal.tags else [],
        macros=deepcopy(meal.macros) if meal.macros else {},
        difficulty=meal.difficulty,
        servings=meal.servings,
        diet_compatibility=deepcopy(meal.diet_compatibility) if meal.diet_compatibility else [],
        goal_fit=deepcopy(meal.goal_fit) if meal.goal_fit else [],
        ingredients=deepcopy(meal.ingredients) if meal.ingredients else [],
        instructions=deepcopy(meal.instructions) if meal.instructions else [],
        cooking_tools=deepcopy(meal.cooking_tools) if meal.cooking_tools else [],
        notes=meal.notes,
        is_favorite=False  # Newly shared meals should start as non-favorites
    )
    db.add(cloned_meal)
    db.flush()
    return cloned_meal
