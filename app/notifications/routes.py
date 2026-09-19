from flask import Blueprint, request
from app.auth.permissions import require_jwt
from app.notifications.service import get_user_notifications, mark_notification_read, mark_all_read
from app.utils.responses import success_response, error_response

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("", methods=["GET"])
@require_jwt
def list_notifications():
    user = request.current_user
    user_id = str(user.get("_id", user.get("id")))
    role = user.get("role")
    unread_only = request.args.get("unread", "false").lower() == "true"
    limit = int(request.args.get("limit", 50))

    notifications = get_user_notifications(user_id, role, unread_only, limit)
    return success_response(data=notifications, message="Notifications fetched")


@notifications_bp.route("/<notification_id>/read", methods=["PUT"])
@require_jwt
def mark_read(notification_id):
    success = mark_notification_read(notification_id)
    if not success:
        return error_response(code="NOT_FOUND", message="Notification not found", status_code=404)
    return success_response(data={"id": notification_id, "is_read": True}, message="Marked as read")


@notifications_bp.route("/read-all", methods=["PUT"])
@require_jwt
def mark_all_as_read():
    user = request.current_user
    user_id = str(user.get("_id", user.get("id")))
    role = user.get("role")
    count = mark_all_read(user_id, role)
    return success_response(data={"updated_count": count}, message=f"Marked {count} notifications as read")
