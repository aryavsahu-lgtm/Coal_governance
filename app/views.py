from flask import Blueprint, render_template, redirect, url_for

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    return render_template("login.html")


@views_bp.route("/login")
def login():
    return render_template("login.html")


@views_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@views_bp.route("/mines-management")
def mines_page():
    return render_template("mines.html")


@views_bp.route("/compliance-board")
def compliance_page():
    return render_template("compliance.html")


@views_bp.route("/inspections-board")
def inspections_page():
    return render_template("inspections.html")


@views_bp.route("/field-reporting")
def field_reporting_page():
    return render_template("field_reporting.html")


@views_bp.route("/violations-board")
def violations_page():
    return render_template("violations.html")


@views_bp.route("/incidents-board")
def incidents_page():
    return render_template("incidents.html")


@views_bp.route("/contractors-board")
def contractors_page():
    return render_template("contractors.html")


@views_bp.route("/documents-vault")
def documents_page():
    return render_template("documents.html")


@views_bp.route("/ai-vision-studio")
def ai_vision_page():
    return render_template("ai_vision.html")


@views_bp.route("/gis-map")
def gis_map_page():
    return render_template("gis_map.html")


@views_bp.route("/analytics-board")
def analytics_page():
    return render_template("analytics.html")


@views_bp.route("/regulatory-assistant")
def rag_assistant_page():
    return render_template("rag_assistant.html")


@views_bp.route("/audit-explorer")
def audit_explorer_page():
    return render_template("audit_logs.html")
