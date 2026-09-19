from flask import Blueprint, request
from app.auth.permissions import require_jwt, check_mine_access
from app.analytics.service import (
    get_executive_analytics_dashboard,
    get_operational_trends_and_anomalies,
    get_public_kpis,
    track_compliance_case,
    get_statutory_notices
)
from app.ai.risk_engine import calculate_mine_risk_score
from app.utils.responses import success_response, error_response

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/dashboard", methods=["GET"])
@require_jwt
def dashboard_analytics():
    user = request.current_user
    mine_id = request.args.get("mine_id")

    if user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    data = get_executive_analytics_dashboard(mine_id)
    return success_response(data=data, message="Governance analytics computed")


@analytics_bp.route("/risk", methods=["GET"])
@require_jwt
def mine_risk():
    mine_id = request.args.get("mine_id")
    if not mine_id:
        return error_response(code="VALIDATION_ERROR", message="mine_id parameter is required", status_code=400)

    risk_info = calculate_mine_risk_score(mine_id)
    return success_response(data=risk_info, message="Explainable risk score calculated")


@analytics_bp.route("/trends-anomalies", methods=["GET"])
@require_jwt
def operational_anomalies():
    mine_id = request.args.get("mine_id")
    data = get_operational_trends_and_anomalies(mine_id)
    return success_response(data=data, message="Operational trends and anomaly analysis computed")


@analytics_bp.route("/search", methods=["GET"])
@require_jwt
def global_search():
    q = request.args.get("q", "").strip()
    mine_id = request.args.get("mine_id")
    category = request.args.get("category")
    severity = request.args.get("severity")
    status = request.args.get("status")

    if not q and not mine_id and not category and not severity and not status:
        return success_response(data={"mines": [], "violations": [], "inspections": [], "incidents": [], "contractors": [], "documents": []}, message="No query criteria provided")

    from app.database import mongo
    regex_q = {"$regex": q, "$options": "i"} if q else None

    # Search Mines
    m_query = {}
    if regex_q:
        m_query["$or"] = [{"mine_name": regex_q}, {"mine_code": regex_q}, {"location": regex_q}]
    mines = list(mongo.mines.find(m_query).limit(10))

    # Search Violations
    v_query = {}
    if regex_q:
        v_query["$or"] = [{"description": regex_q}, {"category": regex_q}]
    if mine_id:
        v_query["mine_id"] = str(mine_id)
    if category:
        v_query["category"] = category
    if severity:
        v_query["severity"] = severity.upper()
    if status:
        v_query["status"] = status.upper()
    violations = list(mongo.violations.find(v_query).limit(15))

    # Search Inspections
    i_query = {}
    if regex_q:
        i_query["$or"] = [{"inspection_type": regex_q}, {"remarks": regex_q}, {"location": regex_q}]
    if mine_id:
        i_query["mine_id"] = str(mine_id)
    if status:
        i_query["status"] = status.upper()
    inspections = list(mongo.inspections.find(i_query).limit(10))

    # Search Incidents
    inc_query = {}
    if regex_q:
        inc_query["$or"] = [{"description": regex_q}, {"incident_type": regex_q}]
    if mine_id:
        inc_query["mine_id"] = str(mine_id)
    if severity:
        inc_query["severity"] = severity.upper()
    incidents = list(mongo.incidents.find(inc_query).limit(10))

    # Search Contractors
    c_query = {}
    if regex_q:
        c_query["$or"] = [{"company_name": regex_q}, {"registration_number": regex_q}]
    if mine_id:
        c_query["mine_id"] = str(mine_id)
    contractors = list(mongo.contractors.find(c_query).limit(10))

    # Search Documents
    d_query = {}
    if regex_q:
        d_query["$or"] = [{"original_filename": regex_q}, {"document_number": regex_q}, {"extracted_text": regex_q}]
    if mine_id:
        d_query["mine_id"] = str(mine_id)
    documents = list(mongo.documents.find(d_query).limit(10))

    return success_response(
        data={
            "query": q,
            "mines": mines,
            "violations": violations,
            "inspections": inspections,
            "incidents": incidents,
            "contractors": contractors,
            "documents": documents
        },
        message="Search results retrieved"
    )


@analytics_bp.route("/public-kpis", methods=["GET"])
def public_kpis():
    data = get_public_kpis()
    return success_response(data=data, message="Public statutory KPIs retrieved")


@analytics_bp.route("/track-case", methods=["GET"])
def track_case_endpoint():
    query = request.args.get("query", "").strip()
    if not query:
        return error_response(code="VALIDATION_ERROR", message="Case reference query is required", status_code=400)
    data = track_compliance_case(query)
    return success_response(data=data, message="Case tracking record resolved")


@analytics_bp.route("/notices", methods=["GET"])
def statutory_notices():
    data = get_statutory_notices()
    return success_response(data=data, message="Statutory safety circulars retrieved")
