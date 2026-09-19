from flask import Blueprint, request
from app.auth.permissions import require_jwt, optional_jwt, require_roles, check_mine_access
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER
from app.mines.service import (
    create_mine,
    update_mine,
    get_mine_by_id,
    list_mines,
    set_mine_status,
    create_zone,
    list_zones,
    get_zone_by_id
)
from app.database import mongo
from app.utils.responses import success_response, error_response

mines_bp = Blueprint("mines", __name__)


@mines_bp.route("", methods=["GET"])
@optional_jwt
def get_all():
    user = getattr(request, "current_user", None)
    subsidiary_id = request.args.get("subsidiary_id")
    
    # If mine officer or safety officer, restrict to their mine unless corporate
    mines = list_mines(subsidiary_id)
    if user and user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine_id = str(user.get("mine_id") or "")
        if user_mine_id:
            mines = [m for m in mines if str(m.get("_id")) == user_mine_id]

    return success_response(data=mines, message="Mines retrieved successfully")


@mines_bp.route("/<mine_id>", methods=["GET"])
@require_jwt
def get_one(mine_id):
    user = request.current_user
    if not check_mine_access(user, mine_id):
        return error_response(code="FORBIDDEN", message="Unauthorized to view this mine", status_code=403)

    mine = get_mine_by_id(mine_id)
    if not mine:
        return error_response(code="NOT_FOUND", message="Mine not found", status_code=404)
    return success_response(data=mine, message="Mine details")


@mines_bp.route("", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT)
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("mine_name") or not data.get("mine_code") or not data.get("subsidiary_id"):
        return error_response(
            code="VALIDATION_ERROR",
            message="mine_name, mine_code, and subsidiary_id are required",
            status_code=400
        )
    
    mine = create_mine(data, user=request.current_user)
    return success_response(data=mine, message="Mine created successfully", status_code=201)


@mines_bp.route("/<mine_id>", methods=["PUT"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER)
def update(mine_id):
    user = request.current_user
    if not check_mine_access(user, mine_id):
        return error_response(code="FORBIDDEN", message="Unauthorized to update this mine", status_code=403)

    data = request.get_json(silent=True) or {}
    updated = update_mine(mine_id, data, user=user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Mine not found", status_code=404)
    return success_response(data=updated, message="Mine updated successfully")


@mines_bp.route("/<mine_id>/status", methods=["PUT"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT)
def change_status(mine_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status or status.upper() not in ("ACTIVE", "INACTIVE", "SUSPENDED"):
        return error_response(code="VALIDATION_ERROR", message="Status must be ACTIVE, INACTIVE, or SUSPENDED", status_code=400)
    
    updated = set_mine_status(mine_id, status, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Mine not found", status_code=404)
    return success_response(data=updated, message="Mine status updated")


# Zone routes
@mines_bp.route("/<mine_id>/zones", methods=["GET"])
@require_jwt
def get_zones_for_mine(mine_id):
    zones = list_zones(mine_id)
    return success_response(data=zones, message="Zones retrieved")


@mines_bp.route("/<mine_id>/zones", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT, ROLE_MINE_OFFICER)
def add_zone_to_mine(mine_id):
    data = request.get_json(silent=True) or {}
    data["mine_id"] = mine_id
    if not data.get("zone_name") or not data.get("zone_code"):
        return error_response(code="VALIDATION_ERROR", message="zone_name and zone_code are required", status_code=400)
    
    zone = create_zone(data, user=request.current_user)
    return success_response(data=zone, message="Zone created successfully", status_code=201)
