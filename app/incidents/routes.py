from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles, check_mine_access
from app.auth.service import (
    ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER,
    ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY
)
from app.incidents.service import (
    report_incident,
    advance_incident_status,
    list_incidents,
    get_incident_by_id,
    INCIDENT_LIFECYCLE
)
from app.utils.responses import success_response, error_response

incidents_bp = Blueprint("incidents", __name__)


@incidents_bp.route("", methods=["GET"])
@require_jwt
def get_all():
    user = request.current_user
    mine_id = request.args.get("mine_id")
    severity = request.args.get("severity")
    status = request.args.get("status")

    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    incidents = list_incidents(mine_id=mine_id, severity=severity, status=status)
    return success_response(data=incidents, message="Incidents retrieved successfully")


@incidents_bp.route("/<incident_id>", methods=["GET"])
@require_jwt
def get_one(incident_id):
    incident = get_incident_by_id(incident_id)
    if not incident:
        return error_response(code="NOT_FOUND", message="Incident not found", status_code=404)
    return success_response(data=incident, message="Incident details")


@incidents_bp.route("", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY)
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("mine_id") or not data.get("description"):
        return error_response(code="VALIDATION_ERROR", message="mine_id and description are required", status_code=400)

    user = request.current_user
    if not check_mine_access(user, data.get("mine_id")):
        return error_response(code="FORBIDDEN", message="Unauthorized for this mine", status_code=403)

    incident = report_incident(data, user=user)
    return success_response(data=incident, message="Incident reported and investigation launched", status_code=201)


@incidents_bp.route("/<incident_id>/advance-status", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY)
def advance(incident_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status", "").upper()
    if status not in INCIDENT_LIFECYCLE:
        return error_response(code="VALIDATION_ERROR", message=f"Status must be one of: {', '.join(INCIDENT_LIFECYCLE)}", status_code=400)

    root_cause = data.get("root_cause")
    notes = data.get("notes")
    corrective_action = data.get("corrective_action")

    updated = advance_incident_status(
        incident_id=incident_id,
        status=status,
        root_cause=root_cause,
        corrective_action=corrective_action,
        notes=notes,
        user=request.current_user
    )
    if not updated:
        return error_response(code="NOT_FOUND", message="Incident not found", status_code=404)
    return success_response(data=updated, message=f"Incident status advanced to {status}")
