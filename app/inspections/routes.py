from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles, check_mine_access
from app.auth.service import (
    ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER,
    ROLE_SAFETY_OFFICER, ROLE_INSPECTION_OFFICER, ROLE_REGULATORY_AUTHORITY
)
from app.inspections.service import (
    create_inspection,
    assign_inspection,
    start_inspection,
    submit_inspection,
    review_inspection,
    close_inspection,
    list_inspections,
    get_inspection_by_id
)
from app.utils.responses import success_response, error_response

inspections_bp = Blueprint("inspections", __name__)


@inspections_bp.route("", methods=["GET"])
@require_jwt
def get_all():
    user = request.current_user
    mine_id = request.args.get("mine_id")
    status = request.args.get("status")
    officer_id = request.args.get("officer_id")

    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine
    elif user.get("role") == ROLE_INSPECTION_OFFICER:
        officer_id = str(user.get("_id", user.get("id")))

    inspections = list_inspections(mine_id=mine_id, status=status, officer_id=officer_id)
    return success_response(data=inspections, message="Inspections retrieved successfully")


@inspections_bp.route("/<inspection_id>", methods=["GET"])
@require_jwt
def get_one(inspection_id):
    inspection = get_inspection_by_id(inspection_id)
    if not inspection:
        return error_response(code="NOT_FOUND", message="Inspection not found", status_code=404)
    return success_response(data=inspection, message="Inspection details")


@inspections_bp.route("", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY)
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("mine_id"):
        return error_response(code="VALIDATION_ERROR", message="mine_id is required", status_code=400)
    
    user = request.current_user
    if not check_mine_access(user, data.get("mine_id")):
        return error_response(code="FORBIDDEN", message="Unauthorized to create inspection for this mine", status_code=403)

    inspection = create_inspection(data, user=user)
    return success_response(data=inspection, message="Inspection created successfully", status_code=201)


@inspections_bp.route("/<inspection_id>/assign", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER)
def assign(inspection_id):
    data = request.get_json(silent=True) or {}
    officer_id = data.get("officer_id")
    if not officer_id:
        return error_response(code="VALIDATION_ERROR", message="officer_id is required", status_code=400)

    updated = assign_inspection(inspection_id, officer_id, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Inspection not found", status_code=404)
    return success_response(data=updated, message="Inspection assigned")


@inspections_bp.route("/<inspection_id>/start", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_INSPECTION_OFFICER, ROLE_SAFETY_OFFICER, ROLE_MINE_OFFICER)
def start(inspection_id):
    updated = start_inspection(inspection_id, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Inspection not found", status_code=404)
    return success_response(data=updated, message="Inspection marked as In Progress")


@inspections_bp.route("/<inspection_id>/submit", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_INSPECTION_OFFICER, ROLE_SAFETY_OFFICER, ROLE_MINE_OFFICER)
def submit(inspection_id):
    data = request.get_json(silent=True) or {}
    observations = data.get("observations", [])
    photos = data.get("photos", [])
    videos = data.get("videos", [])
    severity = data.get("severity", "LOW")
    remarks = data.get("remarks", "")

    updated = submit_inspection(
        inspection_id=inspection_id,
        observations=observations,
        photos=photos,
        videos=videos,
        severity=severity,
        remarks=remarks,
        user=request.current_user
    )
    if not updated:
        return error_response(code="NOT_FOUND", message="Inspection not found", status_code=404)
    return success_response(data=updated, message="Inspection submitted for review")


@inspections_bp.route("/<inspection_id>/review", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY)
def review(inspection_id):
    data = request.get_json(silent=True) or {}
    remarks = data.get("remarks", "")
    updated = review_inspection(inspection_id, remarks, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Inspection not found", status_code=404)
    return success_response(data=updated, message="Inspection reviewed")


@inspections_bp.route("/<inspection_id>/close", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY)
def close(inspection_id):
    data = request.get_json(silent=True) or {}
    closure_remarks = data.get("closure_remarks", "Closed after statutory review")
    updated = close_inspection(inspection_id, closure_remarks, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Inspection not found", status_code=404)
    return success_response(data=updated, message="Inspection closed successfully")
