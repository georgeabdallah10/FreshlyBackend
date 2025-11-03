# crud/meal_share_requests.py
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.meal_share_request import MealShareRequest
from models.meal import Meal
from models.membership import FamilyMembership
from schemas.meal_share_request import MealShareRequestCreate
from typing import List, Optional
from datetime import datetime


def create_share_request(
    db: Session,
    data: MealShareRequestCreate,
    sender_user_id: int,
    family_id: int
) -> MealShareRequest:
    """Create a new meal share request"""
    request = MealShareRequest(
        meal_id=data.meal_id,
        sender_user_id=sender_user_id,
        recipient_user_id=data.recipient_user_id,
        family_id=family_id,
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


def accept_share_request(db: Session, request: MealShareRequest) -> MealShareRequest:
    """Accept a meal share request"""
    request.status = "accepted"
    request.responded_at = datetime.now()
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


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
    # Get all accepted requests where user is recipient
    accepted_requests = db.query(MealShareRequest).filter(
        MealShareRequest.recipient_user_id == user_id,
        MealShareRequest.status == "accepted"
    ).all()
    
    # Extract meal IDs
    meal_ids = [req.meal_id for req in accepted_requests]
    
    # Get the meals
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
