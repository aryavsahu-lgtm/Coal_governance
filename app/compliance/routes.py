from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles, check_mine_access
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_ENVIRONMENTAL_OFFICER, ROLE_REGULATORY_AUTHORITY
from app.compliance.service import (
    create_compliance_requirement,
    list_compliance_requirements,
    update_compliance_status,
    get_compliance_dashboard_metrics,
    COMPLIANCE_STATUSES,
    COMPLIANCE_CATEGORIES
)
from app.utils.responses import success_response, error_response

compliance_bp = Blueprint("compliance", __name__)


@compliance_bp.route("", methods=["GET"])
@require_jwt
def get_all():
    user = request.current_user
    mine_id = request.args.get("mine_id")
    category = request.args.get("category")
    status = request.args.get("status")

    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    items = list_compliance_requirements(mine_id=mine_id, category=category, status=status)
    return success_response(data=items, message="Compliance requirements retrieved")


@compliance_bp.route("/dashboard", methods=["GET"])
@require_jwt
def dashboard_metrics():
    user = request.current_user
    mine_id = request.args.get("mine_id")
    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    metrics = get_compliance_dashboard_metrics(mine_id)
    return success_response(data=metrics, message="Compliance metrics computed")


@compliance_bp.route("", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_ENVIRONMENTAL_OFFICER)
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("title") or not data.get("applicable_mine"):
        return error_response(code="VALIDATION_ERROR", message="Title and applicable_mine are required", status_code=400)
    
    user = request.current_user
    if not check_mine_access(user, data.get("applicable_mine")):
        return error_response(code="FORBIDDEN", message="Unauthorized to create compliance for this mine", status_code=403)

    req = create_compliance_requirement(data, user=user)
    return success_response(data=req, message="Compliance requirement created", status_code=201)


@compliance_bp.route("/<req_id>/status", methods=["PUT"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_ENVIRONMENTAL_OFFICER, ROLE_REGULATORY_AUTHORITY)
def change_status(req_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status", "").upper()
    if status not in COMPLIANCE_STATUSES:
        return error_response(code="VALIDATION_ERROR", message=f"Status must be one of: {', '.join(COMPLIANCE_STATUSES)}", status_code=400)

    evidence = data.get("evidence")
    remarks = data.get("remarks")

    updated = update_compliance_status(req_id, status=status, evidence=evidence, remarks=remarks, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Requirement not found", status_code=404)

    return success_response(data=updated, message="Compliance status updated")
