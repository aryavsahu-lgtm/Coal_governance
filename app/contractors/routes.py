from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles, check_mine_access
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER
from app.contractors.service import (
    create_contractor,
    update_contractor,
    list_contractors,
    get_contractor_by_id,
    calculate_contractor_risk
)
from app.utils.responses import success_response, error_response

contractors_bp = Blueprint("contractors", __name__)


@contractors_bp.route("", methods=["GET"])
@require_jwt
def get_all():
    user = request.current_user
    mine_id = request.args.get("mine_id")
    compliance_status = request.args.get("compliance_status")

    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    contractors = list_contractors(mine_id=mine_id, compliance_status=compliance_status)
    return success_response(data=contractors, message="Contractors retrieved")


@contractors_bp.route("/<contractor_id>", methods=["GET"])
@require_jwt
def get_one(contractor_id):
    contractor = get_contractor_by_id(contractor_id)
    if not contractor:
        return error_response(code="NOT_FOUND", message="Contractor not found", status_code=404)
    return success_response(data=contractor, message="Contractor details")


@contractors_bp.route("", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER)
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("company_name") or not data.get("mine_id"):
        return error_response(code="VALIDATION_ERROR", message="company_name and mine_id are required", status_code=400)

    user = request.current_user
    if not check_mine_access(user, data.get("mine_id")):
        return error_response(code="FORBIDDEN", message="Unauthorized for this mine", status_code=403)

    contractor = create_contractor(data, user=user)
    return success_response(data=contractor, message="Contractor registered successfully", status_code=201)


@contractors_bp.route("/<contractor_id>/risk", methods=["GET"])
@require_jwt
def get_risk(contractor_id):
    risk_info = calculate_contractor_risk(contractor_id)
    return success_response(data=risk_info, message="Explainable contractor risk score computed")
