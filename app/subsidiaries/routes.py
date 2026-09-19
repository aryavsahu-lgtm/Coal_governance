from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_CORPORATE_MANAGEMENT
from app.subsidiaries.service import create_subsidiary, list_subsidiaries, get_subsidiary_by_id
from app.utils.responses import success_response, error_response

subsidiaries_bp = Blueprint("subsidiaries", __name__)


@subsidiaries_bp.route("", methods=["GET"])
@require_jwt
def get_all():
    subs = list_subsidiaries()
    return success_response(data=subs, message="Subsidiaries fetched successfully")


@subsidiaries_bp.route("/<sub_id>", methods=["GET"])
@require_jwt
def get_one(sub_id):
    sub = get_subsidiary_by_id(sub_id)
    if not sub:
        return error_response(code="NOT_FOUND", message="Subsidiary not found", status_code=404)
    return success_response(data=sub, message="Subsidiary details")


@subsidiaries_bp.route("", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN)
def create():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("code"):
        return error_response(code="VALIDATION_ERROR", message="Name and code are required", status_code=400)
    
    sub = create_subsidiary(data, user=request.current_user)
    return success_response(data=sub, message="Subsidiary created", status_code=201)
