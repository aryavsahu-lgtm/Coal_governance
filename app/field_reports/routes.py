from flask import Blueprint, request
from app.auth.permissions import require_jwt, check_mine_access
from app.field_reports.service import submit_field_report, list_field_reports, get_field_report_by_id
from app.utils.responses import success_response, error_response

field_reports_bp = Blueprint("field_reports", __name__)


@field_reports_bp.route("", methods=["POST"])
@require_jwt
def submit():
    data = request.get_json(silent=True) or {}
    if not data.get("mine_id") or not data.get("observation"):
        return error_response(code="VALIDATION_ERROR", message="mine_id and observation are required", status_code=400)
    
    report = submit_field_report(data, user=request.current_user)
    return success_response(data=report, message="Field report submitted successfully", status_code=201)


@field_reports_bp.route("/sync-batch", methods=["POST"])
@require_jwt
def sync_batch():
    """Endpoint for offline-synced batch queue submission."""
    data = request.get_json(silent=True) or {}
    reports = data.get("reports", [])
    if not isinstance(reports, list):
        return error_response(code="VALIDATION_ERROR", message="'reports' must be an array", status_code=400)
    
    synced = []
    for r in reports:
        r["is_synced_from_offline"] = True
        saved = submit_field_report(r, user=request.current_user)
        synced.append(saved)

    return success_response(data=synced, message=f"Successfully synced {len(synced)} offline field reports", status_code=201)


@field_reports_bp.route("", methods=["GET"])
@require_jwt
def get_all():
    user = request.current_user
    mine_id = request.args.get("mine_id")
    zone_id = request.args.get("zone_id")

    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    reports = list_field_reports(mine_id=mine_id, zone_id=zone_id)
    return success_response(data=reports, message="Field reports retrieved")


@field_reports_bp.route("/<report_id>", methods=["GET"])
@require_jwt
def get_one(report_id):
    report = get_field_report_by_id(report_id)
    if not report:
        return error_response(code="NOT_FOUND", message="Report not found", status_code=404)
    return success_response(data=report, message="Field report details")
