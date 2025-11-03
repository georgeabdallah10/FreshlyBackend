# crud/notifications.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from models.notification import Notification
from schemas.notification import NotificationCreate
from typing import List, Optional, Dict
from datetime import datetime


def create_notification(db: Session, data: NotificationCreate) -> Notification:
    """Create a new notification"""
    notification = Notification(
        user_id=data.user_id,
        type=data.type,
        title=data.title,
        message=data.message,
        related_meal_id=data.related_meal_id,
        related_user_id=data.related_user_id,
        related_family_id=data.related_family_id,
        related_share_request_id=data.related_share_request_id,
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_notification(db: Session, notification_id: int) -> Optional[Notification]:
    """Get a single notification by ID"""
    return db.query(Notification).filter(Notification.id == notification_id).first()


def get_user_notifications(
    db: Session,
    user_id: int,
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[Notification]:
    """Get all notifications for a user with optional filters"""
    query = db.query(Notification).filter(Notification.user_id == user_id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    if notification_type:
        query = query.filter(Notification.type == notification_type)
    
    return query.order_by(desc(Notification.created_at)).offset(skip).limit(limit).all()


def get_unread_count(db: Session, user_id: int) -> int:
    """Get count of unread notifications for a user"""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).count()


def get_notification_stats(db: Session, user_id: int) -> Dict:
    """Get notification statistics for a user"""
    total = db.query(Notification).filter(Notification.user_id == user_id).count()
    unread = get_unread_count(db, user_id)
    
    # Get unread count by type
    unread_by_type = db.query(
        Notification.type,
        func.count(Notification.id)
    ).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).group_by(Notification.type).all()
    
    unread_by_type_dict = {type_: count for type_, count in unread_by_type}
    
    return {
        "total": total,
        "unread": unread,
        "unread_by_type": unread_by_type_dict
    }


def mark_as_read(db: Session, notification: Notification) -> Notification:
    """Mark a notification as read"""
    notification.is_read = True
    notification.read_at = datetime.now()
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_as_unread(db: Session, notification: Notification) -> Notification:
    """Mark a notification as unread"""
    notification.is_read = False
    notification.read_at = None
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, user_id: int) -> int:
    """Mark all notifications as read for a user. Returns count of updated notifications."""
    now = datetime.now()
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": now
    }, synchronize_session=False)
    
    db.commit()
    return count


def delete_notification(db: Session, notification: Notification):
    """Delete a notification"""
    db.delete(notification)
    db.commit()


def delete_all_read_notifications(db: Session, user_id: int) -> int:
    """Delete all read notifications for a user. Returns count of deleted notifications."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == True
    ).delete(synchronize_session=False)
    
    db.commit()
    return count


def delete_all_notifications(db: Session, user_id: int) -> int:
    """Delete all notifications for a user. Returns count of deleted notifications."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id
    ).delete(synchronize_session=False)
    
    db.commit()
    return count


# Helper functions for creating specific notification types

def create_meal_share_request_notification(
    db: Session,
    receiver_id: int,
    sender_name: str,
    meal_name: str,
    share_request_id: int,
    meal_id: int,
    sender_id: int
) -> Notification:
    """Create a notification for a new meal share request"""
    data = NotificationCreate(
        userId=receiver_id,
        type="meal_share_request",
        title="New Meal Share Request",
        message=f"{sender_name} wants to share '{meal_name}' with you",
        relatedMealId=meal_id,
        relatedUserId=sender_id,
        relatedShareRequestId=share_request_id
    )
    return create_notification(db, data)


def create_meal_share_accepted_notification(
    db: Session,
    sender_id: int,
    receiver_name: str,
    meal_name: str,
    share_request_id: int,
    meal_id: int,
    receiver_id: int
) -> Notification:
    """Create a notification when meal share is accepted"""
    data = NotificationCreate(
        userId=sender_id,
        type="meal_share_accepted",
        title="Meal Share Accepted",
        message=f"{receiver_name} accepted your meal '{meal_name}'",
        relatedMealId=meal_id,
        relatedUserId=receiver_id,
        relatedShareRequestId=share_request_id
    )
    return create_notification(db, data)


def create_meal_share_declined_notification(
    db: Session,
    sender_id: int,
    receiver_name: str,
    meal_name: str,
    share_request_id: int,
    meal_id: int,
    receiver_id: int
) -> Notification:
    """Create a notification when meal share is declined"""
    data = NotificationCreate(
        userId=sender_id,
        type="meal_share_declined",
        title="Meal Share Declined",
        message=f"{receiver_name} declined your meal '{meal_name}'",
        relatedMealId=meal_id,
        relatedUserId=receiver_id,
        relatedShareRequestId=share_request_id
    )
    return create_notification(db, data)


def create_family_member_joined_notification(
    db: Session,
    family_owner_id: int,
    new_member_name: str,
    family_name: str,
    family_id: int,
    new_member_id: int
) -> Notification:
    """Create a notification when someone joins a family"""
    data = NotificationCreate(
        userId=family_owner_id,
        type="family_member_joined",
        title="New Family Member",
        message=f"{new_member_name} joined your family '{family_name}'",
        relatedFamilyId=family_id,
        relatedUserId=new_member_id
    )
    return create_notification(db, data)
