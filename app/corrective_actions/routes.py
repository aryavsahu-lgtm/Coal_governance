from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_REGULATORY_AUTHORITY
from app.corrective_actions.service import (
    submit_capa_evidence,
    verify_capa,
    auto_verify_capa,
    list_corrective_actions,
    get_corrective_action_by_id
)
from app.utils.responses import success_response, error_response

corrective_actions_bp = Blueprint("corrective_actions", __name__)


@corrective_actions_bp.route("", methods=["GET"])
@require_jwt
def get_all():
    user = request.current_user
    mine_id = request.args.get("mine_id")
    status = request.args.get("status")
    assigned_to = request.args.get("assigned_to")

    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    actions = list_corrective_actions(mine_id=mine_id, assigned_to=assigned_to, status=status)
    return success_response(data=actions, message="Corrective actions retrieved")


@corrective_actions_bp.route("/<action_id>", methods=["GET"])
@require_jwt
def get_one(action_id):
    action = get_corrective_action_by_id(action_id)
    if not action:
        return error_response(code="NOT_FOUND", message="Corrective action not found", status_code=404)
    return success_response(data=action, message="Corrective action details")


@corrective_actions_bp.route("/<action_id>/submit-evidence", methods=["POST"])
@require_jwt
def submit_evidence(action_id):
    data = request.get_json(silent=True) or {}
    evidence = data.get("evidence", [])
    notes = data.get("notes", "")

    updated = submit_capa_evidence(action_id, evidence=evidence, notes=notes, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Corrective action not found", status_code=404)
    return success_response(data=updated, message="Evidence submitted for verification")


@corrective_actions_bp.route("/<action_id>/verify", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_SAFETY_OFFICER, ROLE_MINE_OFFICER, ROLE_REGULATORY_AUTHORITY)
def verify(action_id):
    data = request.get_json(silent=True) or {}
    status = data.get("status", "VERIFIED").upper()
    remarks = data.get("remarks", "")

    if status not in ("VERIFIED", "REJECTED"):
        return error_response(code="VALIDATION_ERROR", message="Status must be VERIFIED or REJECTED", status_code=400)

    updated = verify_capa(action_id, status=status, remarks=remarks, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Corrective action not found", status_code=404)
    return success_response(data=updated, message=f"Corrective action has been {status}")


@corrective_actions_bp.route("/<action_id>/auto-verify", methods=["POST"])
@require_jwt
def auto_verify(action_id):
    updated = auto_verify_capa(action_id, user=request.current_user)
    if not updated:
        return error_response(code="NOT_FOUND", message="Corrective action not found", status_code=404)
    return success_response(data=updated, message="Corrective action automatically verified via AI surveillance clearance")

