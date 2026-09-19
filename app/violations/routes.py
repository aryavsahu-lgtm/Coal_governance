from flask import Blueprint, request
from app.auth.permissions import require_jwt, optional_jwt, require_roles, check_mine_access
from app.auth.service import (
    ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER,
    ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY
)
from app.violations.service import (
    create_violation,
    assign_violation,
    acknowledge_violation,
    close_violation,
    list_violations,
    get_violation_by_id
)
from app.utils.responses import success_response, error_response

violations_bp = Blueprint("violations", __name__)


@violations_bp.route("", methods=["GET"])
@optional_jwt
def get_all():
    user = getattr(request, "current_user", None)
    mine_id = request.args.get("mine_id")
    severity = request.args.get("severity")
    status = request.args.get("status")

    if user and user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    violations = list_violations(mine_id=mine_id, severity=severity, status=status)
    return success_response(data=violations, message="Violations retrieved successfully")


@violations_bp.route("/<violation_id>", methods=["GET"])
@require_jwt
def get_one(violation_id):
    violation = get_violation_by_id(violation_id)
    if not violation:
        return error_response(code="NOT_FOUND", message="Violation not found", status_code=404)
    return success_response(data=violation, message="Violation details")


@violations_bp.route("", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY)
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("mine_id") or not data.get("description"):
        return error_response(code="VALIDATION_ERROR", message="mine_id and description are required", status_code=400)

    user = request.current_user
    if not check_mine_access(user, data.get("mine_id")):
        return error_response(code="FORBIDDEN", message="Unauthorized for this mine", status_code=403)

    violation = create_violation(data, user=user)
    return success_response(data=violation, message="Violation created and CAPA dispatched", status_code=201)


@violations_bp.route("/<violation_id>/assign", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER)
def assign(violation_id):
    data = request.get_json(silent=True) or {}
    officer_id = data.get("officer_id")
    if not officer_id:
        return error_response(code="VALIDATION_ERROR", message="officer_id is required", status_code=400)

    updated = assign_violation(violation_id, officer_id, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Violation not found", status_code=404)
    return success_response(data=updated, message="Violation assigned successfully")


@violations_bp.route("/<violation_id>/acknowledge", methods=["POST"])
@require_jwt
def acknowledge(violation_id):
    updated = acknowledge_violation(violation_id, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Violation not found", status_code=404)
    return success_response(data=updated, message="Violation acknowledged")


@violations_bp.route("/<violation_id>/close", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY)
def close(violation_id):
    data = request.get_json(silent=True) or {}
    closure_notes = data.get("closure_notes", "Verified and closed by authorized safety officer")
    
    updated = close_violation(violation_id, closure_notes, user=request.current_user)
    if not updated:
        return error_response(
            code="UNVERIFIED_CLOSURE_PREVENTED",
            message="Cannot close violation: Corrective Action proof has not been verified by an authorized officer yet.",
            status_code=400
        )
    return success_response(data=updated, message="Violation successfully closed")
