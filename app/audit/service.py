import datetime
import logging
from typing import Optional, Dict, Any
from flask import request
from app.database import mongo

logger = logging.getLogger("coal_governance.audit")


def log_audit_event(
    action: str,
    entity: str,
    entity_id: str,
    user: Optional[Dict[str, Any]] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """Append-only audit trail event recorder."""
    try:
        ip_addr = None
        user_agent = None
        user_id = "SYSTEM"
        user_email = "system@internal"
        user_role = "SYSTEM"

        if request:
            ip_addr = request.headers.get("X-Forwarded-For", request.remote_addr)
            user_agent = request.headers.get("User-Agent", "")

        if user:
            user_id = str(user.get("_id", user.get("id", user.get("user_id", "ANONYMOUS"))))
            user_email = user.get("email", "unknown")
            user_role = user.get("role", "UNKNOWN")
        elif request and hasattr(request, "current_user") and request.current_user:
            cu = request.current_user
            user_id = str(cu.get("_id", cu.get("id", "ANONYMOUS")))
            user_email = cu.get("email", "unknown")
            user_role = cu.get("role", "UNKNOWN")

        audit_entry = {
            "timestamp": datetime.datetime.utcnow(),
            "action": action.upper(),
            "entity": entity.upper(),
            "entity_id": str(entity_id),
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "old_value": old_value,
            "new_value": new_value,
            "notes": notes,
            "ip_address": ip_addr,
            "user_agent": user_agent
        }

        mongo.audit_logs.insert_one(audit_entry)
        return audit_entry
    except Exception as e:
        logger.error(f"Failed to record audit log: {e}")
        return {}
