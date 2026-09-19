from flask import Blueprint, request
from app.auth.permissions import require_roles
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_REGULATORY_AUTHORITY, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER
from app.database import mongo
from app.utils.responses import success_response

audit_bp = Blueprint("audit", __name__)


@audit_bp.route("", methods=["GET"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_REGULATORY_AUTHORITY, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER)
def get_audit_logs():
    query = {}
    action = request.args.get("action")
    entity = request.args.get("entity")
    entity_id = request.args.get("entity_id")
    user_id = request.args.get("user_id")
    limit = int(request.args.get("limit", 100))

    if action:
        query["action"] = action.upper()
    if entity:
        query["entity"] = entity.upper()
    if entity_id:
        query["entity_id"] = entity_id
    if user_id:
        query["user_id"] = user_id

    cursor = mongo.audit_logs.find(query).sort("timestamp", -1).limit(limit)
    logs = list(cursor)
    return success_response(data=logs, message=f"Retrieved {len(logs)} audit logs")
