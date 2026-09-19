from flask import Blueprint, request
from app.auth.permissions import require_jwt, require_roles
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_SAFETY_OFFICER, ROLE_MINE_OFFICER
from app.database import mongo
from app.workflow.rule_engine import seed_default_rules
from app.workflow.escalation import process_escalations
from app.utils.responses import success_response, error_response

workflow_bp = Blueprint("rules", __name__)


@workflow_bp.route("", methods=["GET"])
@require_jwt
def list_rules():
    seed_default_rules()
    rules = list(mongo.rules.find())
    return success_response(data=rules, message="Configurable rules retrieved")


@workflow_bp.route("/<rule_id>/toggle", methods=["PUT"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_SAFETY_OFFICER)
def toggle_rule(rule_id):
    data = request.get_json(silent=True) or {}
    enabled = data.get("enabled")
    if enabled is None:
        return error_response(code="VALIDATION_ERROR", message="'enabled' boolean required", status_code=400)

    res = mongo.rules.update_one({"rule_id": rule_id}, {"$set": {"enabled": bool(enabled)}})
    if res.matched_count == 0:
        return error_response(code="NOT_FOUND", message="Rule not found", status_code=404)

    return success_response(data={"rule_id": rule_id, "enabled": bool(enabled)}, message="Rule updated")


@workflow_bp.route("/escalate-check", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER)
def trigger_escalation_sweep():
    summary = process_escalations()
    return success_response(data=summary, message="Escalation sweep executed successfully")
