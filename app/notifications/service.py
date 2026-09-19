import datetime
import logging
from typing import Optional, List, Dict, Any
from bson import ObjectId
from app.database import mongo

logger = logging.getLogger("coal_governance.notifications")


def create_notification(
    user_id: Optional[str],
    role: Optional[str],
    title: str,
    message: str,
    event_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    severity: str = "INFO"
) -> Dict[str, Any]:
    """
    Creates an in-app notification and dispatches to notification channels.
    Supports user-specific or role-wide notifications.
    """
    notification_doc = {
        "user_id": str(user_id) if user_id else None,
        "target_role": role,
        "title": title,
        "message": message,
        "event_type": event_type,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id else None,
        "severity": severity.upper(),
        "is_read": False,
        "created_at": datetime.datetime.utcnow()
    }
    
    res = mongo.notifications.insert_one(notification_doc)
    notification_doc["_id"] = res.inserted_id

    # Extensible dispatch channels (SMS/Email/Push ready)
    _dispatch_external_channels(notification_doc)

    return notification_doc


def _dispatch_external_channels(notification: Dict[str, Any]):
    """Extensible stub for SMS, SMTP Email, or Web Push dispatchers."""
    logger.info(f"[Notification Dispatch] ({notification['severity']}) Event: {notification['event_type']} -> Title: {notification['title']}")


def get_user_notifications(user_id: str, role: str, unread_only: bool = False, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve notifications targeted to this user or their role."""
    query = {
        "$or": [
            {"user_id": str(user_id)},
            {"target_role": role},
            {"target_role": "ALL"}
        ]
    }
    if unread_only:
        query["is_read"] = False

    cursor = mongo.notifications.find(query).sort("created_at", -1).limit(limit)
    return list(cursor)


def mark_notification_read(notification_id: str) -> bool:
    """Mark a single notification as read."""
    query = {"_id": ObjectId(notification_id)} if ObjectId.is_valid(notification_id) else {"_id": notification_id}
    res = mongo.notifications.update_one(query, {"$set": {"is_read": True, "read_at": datetime.datetime.utcnow()}})
    return res.matched_count > 0


def mark_all_read(user_id: str, role: str) -> int:
    """Mark all notifications as read for a user."""
    query = {
        "$or": [
            {"user_id": str(user_id)},
            {"target_role": role}
        ],
        "is_read": False
    }
    res = mongo.notifications.update_many(query, {"$set": {"is_read": True, "read_at": datetime.datetime.utcnow()}})
    return res.modified_count
