# routers/meal_share_requests.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user
from models.user import User
from models.membership import FamilyMembership
from models.meal import Meal
from crud.meal_share_requests import (
    create_share_request,
    get_share_request,
    get_pending_requests_for_user,
    get_sent_requests,
    get_received_requests,
    accept_share_request,
    decline_share_request,
    get_accepted_meals_for_user,
    check_existing_request,
    delete_share_request
)
from crud.meals import get_meal
from crud.notifications import (
    create_meal_share_request_notification,
    create_meal_share_accepted_notification,
    create_meal_share_declined_notification
)
from schemas.meal_share_request import (
    MealShareRequestCreate,
    MealShareRequestOut,
    MealShareRequestResponse
)
from schemas.meal import MealOut

router = APIRouter(prefix="/meal-share-requests", tags=["meal-share-requests"])


@router.post("", response_model=MealShareRequestOut, status_code=status.HTTP_201_CREATED)
def send_meal_share_request(
    data: MealShareRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a meal share request to a specific family member"""
    
    # Get the meal
    meal = get_meal(db, data.meal_id)
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Meal not found"}
        )
    
    # Verify user owns the meal
    if meal.created_by_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "You can only share meals you own"}
        )
    
    # Check if meal belongs to a family
    if not meal.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Meal must belong to a family to be shared"}
        )
    
    # Check if user is trying to send to themselves
    if current_user.id == data.recipient_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "You cannot send a share request to yourself"}
        )
    
    # Check if sender and recipient are in the same family
    sender_membership = db.query(FamilyMembership).filter(
        FamilyMembership.family_id == meal.family_id,
        FamilyMembership.user_id == current_user.id
    ).first()
    
    recipient_membership = db.query(FamilyMembership).filter(
        FamilyMembership.family_id == meal.family_id,
        FamilyMembership.user_id == data.recipient_user_id
    ).first()
    
    if not sender_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "You must be a member of the meal's family to share it"}
        )
    
    if not recipient_membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Recipient must be a member of the meal's family"}
        )
    
    # Check if a pending request already exists
    existing = check_existing_request(db, data.meal_id, current_user.id, data.recipient_user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "A pending request already exists for this meal and recipient"}
        )
    
    # Create the request
    request = create_share_request(db, data, current_user.id, meal.family_id)
    
    # Create notification for the receiver
    create_meal_share_request_notification(
        db,
        receiver_id=data.recipient_user_id,
        sender_name=current_user.name or current_user.email,
        meal_name=meal.name,
        share_request_id=request.id,
        meal_id=meal.id,
        sender_id=current_user.id
    )
    
    # Build response with additional data
    return MealShareRequestOut(
        id=request.id,
        mealId=request.meal_id,
        senderUserId=request.sender_user_id,
        recipientUserId=request.recipient_user_id,
        familyId=request.family_id,
        status=request.status,
        message=request.message,
        createdAt=request.created_at,
        updatedAt=request.updated_at,
        respondedAt=request.responded_at,
        mealName=request.meal.name if request.meal else None,
        senderName=request.sender.name if request.sender else None,
        recipientName=request.recipient.name if request.recipient else None
    )


@router.get("/pending", response_model=list[MealShareRequestOut])
def get_my_pending_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all pending meal share requests sent to me"""
    requests = get_pending_requests_for_user(db, current_user.id)
    
    return [
        MealShareRequestOut(
            id=req.id,
            mealId=req.meal_id,
            senderUserId=req.sender_user_id,
            recipientUserId=req.recipient_user_id,
            familyId=req.family_id,
            status=req.status,
            message=req.message,
            createdAt=req.created_at,
            updatedAt=req.updated_at,
            respondedAt=req.responded_at,
            mealName=req.meal.name if req.meal else None,
            senderName=req.sender.name if req.sender else None,
            recipientName=req.recipient.name if req.recipient else None
        )
        for req in requests
    ]


@router.get("/sent", response_model=list[MealShareRequestOut])
def get_my_sent_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all meal share requests I've sent"""
    requests = get_sent_requests(db, current_user.id)
    
    return [
        MealShareRequestOut(
            id=req.id,
            mealId=req.meal_id,
            senderUserId=req.sender_user_id,
            recipientUserId=req.recipient_user_id,
            familyId=req.family_id,
            status=req.status,
            message=req.message,
            createdAt=req.created_at,
            updatedAt=req.updated_at,
            respondedAt=req.responded_at,
            mealName=req.meal.name if req.meal else None,
            senderName=req.sender.name if req.sender else None,
            recipientName=req.recipient.name if req.recipient else None
        )
        for req in requests
    ]


@router.get("/received", response_model=list[MealShareRequestOut])
def get_my_received_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all meal share requests I've received"""
    requests = get_received_requests(db, current_user.id)
    
    return [
        MealShareRequestOut(
            id=req.id,
            mealId=req.meal_id,
            senderUserId=req.sender_user_id,
            recipientUserId=req.recipient_user_id,
            familyId=req.family_id,
            status=req.status,
            message=req.message,
            createdAt=req.created_at,
            updatedAt=req.updated_at,
            respondedAt=req.responded_at,
            mealName=req.meal.name if req.meal else None,
            senderName=req.sender.name if req.sender else None,
            recipientName=req.recipient.name if req.recipient else None
        )
        for req in requests
    ]


@router.post("/{request_id}/respond", response_model=MealShareRequestOut)
def respond_to_share_request(
    request_id: int,
    response: MealShareRequestResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept or decline a meal share request"""
    
    # Get the request
    share_request = get_share_request(db, request_id)
    if not share_request:
        raise HTTPException(status_code=404, detail="Share request not found")
    
    # Check if current user is the recipient
    if share_request.recipient_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the recipient can respond to this request")
    
    # Check if already responded
    if share_request.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request has already been {share_request.status}")
    
    # Accept or decline
    if response.action == "accept":
        updated_request = accept_share_request(db, share_request)
        # Create notification for sender
        create_meal_share_accepted_notification(
            db,
            sender_id=share_request.sender_user_id,
            receiver_name=current_user.name or current_user.email,
            meal_name=share_request.meal.name if share_request.meal else "meal",
            share_request_id=share_request.id,
            meal_id=share_request.meal_id,
            receiver_id=current_user.id
        )
    else:
        updated_request = decline_share_request(db, share_request)
        # Create notification for sender
        create_meal_share_declined_notification(
            db,
            sender_id=share_request.sender_user_id,
            receiver_name=current_user.name or current_user.email,
            meal_name=share_request.meal.name if share_request.meal else "meal",
            share_request_id=share_request.id,
            meal_id=share_request.meal_id,
            receiver_id=current_user.id
        )
    
    return MealShareRequestOut(
        id=updated_request.id,
        mealId=updated_request.meal_id,
        senderUserId=updated_request.sender_user_id,
        recipientUserId=updated_request.recipient_user_id,
        familyId=updated_request.family_id,
        status=updated_request.status,
        message=updated_request.message,
        createdAt=updated_request.created_at,
        updatedAt=updated_request.updated_at,
        respondedAt=updated_request.responded_at,
        mealName=updated_request.meal.name if updated_request.meal else None,
        senderName=updated_request.sender.name if updated_request.sender else None,
        recipientName=updated_request.recipient.name if updated_request.recipient else None
    )


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_share_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending meal share request (only sender can cancel)"""
    
    # Get the request
    share_request = get_share_request(db, request_id)
    if not share_request:
        raise HTTPException(status_code=404, detail="Share request not found")
    
    # Check if current user is the sender
    if share_request.sender_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the sender can cancel this request")
    
    # Check if still pending
    if share_request.status != "pending":
        raise HTTPException(status_code=400, detail="Can only cancel pending requests")
    
    delete_share_request(db, share_request)
    return None


@router.get("/accepted-meals", response_model=list[MealOut])
def get_my_accepted_meals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all meals that I've accepted from others"""
    meals = get_accepted_meals_for_user(db, current_user.id)
    return meals
