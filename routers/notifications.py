# routers/notifications.py
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user
from core.rate_limit import rate_limiter_with_user
from models.user import User
from crud.notifications import (
    get_user_notifications,
    get_notification,
    get_unread_count,
    get_notification_stats,
    mark_as_read,
    mark_as_unread,
    mark_all_as_read,
    delete_notification,
    delete_all_read_notifications,
    delete_all_notifications
)
from schemas.notification import NotificationOut, NotificationUpdate, NotificationStats
from typing import Optional, List
from utils.cache import get_cache, invalidate_cache_pattern

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=List[NotificationOut])
def get_my_notifications(
    req: Request,
    unread_only: bool = Query(False, alias="unreadOnly"),
    type: Optional[str] = Query(None, description="Filter by notification type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("notifications"))
):
    """
    Get all notifications for the current user.
    
    Query params:
    - unreadOnly: If true, only return unread notifications
    - type: Filter by notification type (meal_share_request, meal_share_accepted, etc.)
    - skip: Number of notifications to skip (pagination)
    - limit: Max number of notifications to return
    """
    notifications = get_user_notifications(
        db, 
        current_user.id,
        unread_only=unread_only,
        notification_type=type,
        skip=skip,
        limit=limit
    )
    
    # Build response with related data
    result = []
    for notif in notifications:
        result.append(NotificationOut(
            id=notif.id,
            userId=notif.user_id,
            type=notif.type,
            title=notif.title,
            message=notif.message,
            relatedMealId=notif.related_meal_id,
            relatedUserId=notif.related_user_id,
            relatedFamilyId=notif.related_family_id,
            relatedShareRequestId=notif.related_share_request_id,
            isRead=notif.is_read,
            createdAt=notif.created_at,
            readAt=notif.read_at,
            relatedUserName=notif.related_user.name if notif.related_user else None,
            relatedMealName=notif.related_meal.name if notif.related_meal else None,
            relatedFamilyName=notif.related_family.display_name if notif.related_family else None
        ))
    
    return result


@router.get("/unread-count", response_model=dict)
async def get_unread_notification_count(
    req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter_with_user("notifications"))
):
    """Get the count of unread notifications for the current user"""
    # Try cache first
    cache = get_cache()
    cache_key = f"notifications:unread:{current_user.id}"
    cached_count = await cache.get(cache_key)

    if cached_count is not None:
        return {"count": cached_count}

    # Cache miss - fetch from database
    count = get_unread_count(db, current_user.id)

    # Cache for 30 seconds
    await cache.set(cache_key, count, ttl=30)

    return {"count": count}


@router.get("/stats", response_model=NotificationStats)
def get_notification_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification statistics for the current user"""
    stats = get_notification_stats(db, current_user.id)
    return NotificationStats(
        total=stats["total"],
        unread=stats["unread"],
        unreadByType=stats["unread_by_type"]
    )


@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification_by_id(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific notification by ID"""
    notification = get_notification(db, notification_id)
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this notification")
    
    return NotificationOut(
        id=notification.id,
        userId=notification.user_id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        relatedMealId=notification.related_meal_id,
        relatedUserId=notification.related_user_id,
        relatedFamilyId=notification.related_family_id,
        relatedShareRequestId=notification.related_share_request_id,
        isRead=notification.is_read,
        createdAt=notification.created_at,
        readAt=notification.read_at,
        relatedUserName=notification.related_user.name if notification.related_user else None,
        relatedMealName=notification.related_meal.name if notification.related_meal else None,
        relatedFamilyName=notification.related_family.display_name if notification.related_family else None
    )


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific notification as read"""
    notification = get_notification(db, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this notification")

    updated_notification = mark_as_read(db, notification)

    # Invalidate notification cache
    await invalidate_cache_pattern(f"notifications:unread:{current_user.id}")

    return NotificationOut(
        id=updated_notification.id,
        userId=updated_notification.user_id,
        type=updated_notification.type,
        title=updated_notification.title,
        message=updated_notification.message,
        relatedMealId=updated_notification.related_meal_id,
        relatedUserId=updated_notification.related_user_id,
        relatedFamilyId=updated_notification.related_family_id,
        relatedShareRequestId=updated_notification.related_share_request_id,
        isRead=updated_notification.is_read,
        createdAt=updated_notification.created_at,
        readAt=updated_notification.read_at,
        relatedUserName=updated_notification.related_user.name if updated_notification.related_user else None,
        relatedMealName=updated_notification.related_meal.name if updated_notification.related_meal else None,
        relatedFamilyName=updated_notification.related_family.display_name if updated_notification.related_family else None
    )


@router.patch("/{notification_id}/unread", response_model=NotificationOut)
async def mark_notification_as_unread(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a specific notification as unread"""
    notification = get_notification(db, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this notification")

    updated_notification = mark_as_unread(db, notification)

    # Invalidate notification cache
    await invalidate_cache_pattern(f"notifications:unread:{current_user.id}")

    return NotificationOut(
        id=updated_notification.id,
        userId=updated_notification.user_id,
        type=updated_notification.type,
        title=updated_notification.title,
        message=updated_notification.message,
        relatedMealId=updated_notification.related_meal_id,
        relatedUserId=updated_notification.related_user_id,
        relatedFamilyId=updated_notification.related_family_id,
        relatedShareRequestId=updated_notification.related_share_request_id,
        isRead=updated_notification.is_read,
        createdAt=updated_notification.created_at,
        readAt=updated_notification.read_at,
        relatedUserName=updated_notification.related_user.name if updated_notification.related_user else None,
        relatedMealName=updated_notification.related_meal.name if updated_notification.related_meal else None,
        relatedFamilyName=updated_notification.related_family.display_name if updated_notification.related_family else None
    )


@router.post("/mark-all-read", response_model=dict)
async def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read for the current user"""
    count = mark_all_as_read(db, current_user.id)

    # Invalidate notification cache
    await invalidate_cache_pattern(f"notifications:unread:{current_user.id}")

    return {"message": f"Marked {count} notifications as read", "count": count}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_single_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific notification"""
    notification = get_notification(db, notification_id)

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this notification")

    # Check if notification is unread before deletion
    is_unread = not notification.is_read

    delete_notification(db, notification)

    # Invalidate notification cache if unread notification was deleted
    if is_unread:
        await invalidate_cache_pattern(f"notifications:unread:{current_user.id}")

    return None


@router.delete("/read/all", response_model=dict)
async def delete_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete all read notifications for the current user"""
    count = delete_all_read_notifications(db, current_user.id)
    # No need to invalidate cache - only read notifications deleted
    return {"message": f"Deleted {count} read notifications", "count": count}


@router.delete("/all", response_model=dict)
async def delete_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete all notifications for the current user"""
    count = delete_all_notifications(db, current_user.id)

    # Invalidate notification cache (all notifications including unread are deleted)
    await invalidate_cache_pattern(f"notifications:unread:{current_user.id}")

    return {"message": f"Deleted {count} notifications", "count": count}
