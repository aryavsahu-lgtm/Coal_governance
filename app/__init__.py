import logging
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.database import create_indexes, mongo
from app.utils.responses import error_response, success_response

# Setup logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("coal_governance")


def create_app(config_class=Config):
    """Flask Application Factory."""
    Config.ensure_directories()

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    template_dir = frontend_dir / "templates"
    static_dir = frontend_dir / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir)
    )
    app.config.from_object(config_class)

    # Enable CORS for all REST APIs
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Database index initialization and auto-seeding if empty
    with app.app_context():
        create_indexes()
        try:
            if mongo.users.count_documents({}) == 0:
                from app.database.seed_data import seed_database
                logger.info("[Database] Empty database detected. Auto-seeding initial demo data and personas...")
                seed_database()
        except Exception as e:
            logger.warning(f"[Database] Auto-seeding check: {e}")

    # Register Global HTTP Error Handlers with standard JSON envelopes
    @app.errorhandler(400)
    def bad_request(e):
        return error_response(
            code="BAD_REQUEST",
            message=getattr(e, "description", "Bad request"),
            status_code=400
        )

    @app.errorhandler(401)
    def unauthorized(e):
        return error_response(
            code="UNAUTHORIZED",
            message=getattr(e, "description", "Authentication required"),
            status_code=401
        )

    @app.errorhandler(403)
    def forbidden(e):
        return error_response(
            code="FORBIDDEN",
            message=getattr(e, "description", "You do not have permission to perform this action"),
            status_code=403
        )

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return error_response(
                code="NOT_FOUND",
                message=f"The requested endpoint '{request.path}' was not found",
                status_code=404
            )
        # Render generic 404 page or fallback
        return error_response(code="NOT_FOUND", message="Resource not found", status_code=404)

    @app.errorhandler(413)
    def file_too_large(e):
        return error_response(
            code="PAYLOAD_TOO_LARGE",
            message=f"File exceeds maximum allowed size of {Config.MAX_UPLOAD_SIZE // (1024*1024)}MB",
            status_code=413
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            return error_response(
                code=e.name.upper().replace(" ", "_"),
                message=e.description,
                status_code=e.code
            )
        logger.exception(f"Unhandled exception on {request.path}: {e}")
        return error_response(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred. Please consult system logs.",
            status_code=500
        )

    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        db_status = "connected" if not mongo.is_mock else "fallback_in_memory"
        return success_response(
            data={
                "status": "healthy",
                "database_mode": db_status,
                "database_error": mongo.connection_error,
                "mock_ai_enabled": Config.ENABLE_MOCK_AI,
                "version": "1.0.0"
            },
            message="CoalGov-AI platform is operational"
        )

    # Register Blueprints
    from app.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/api/auth")

    from app.subsidiaries.routes import subsidiaries_bp
    app.register_blueprint(subsidiaries_bp, url_prefix="/api/subsidiaries")

    from app.mines.routes import mines_bp
    app.register_blueprint(mines_bp, url_prefix="/api/mines")

    from app.compliance.routes import compliance_bp
    app.register_blueprint(compliance_bp, url_prefix="/api/compliance")

    from app.inspections.routes import inspections_bp
    app.register_blueprint(inspections_bp, url_prefix="/api/inspections")

    from app.field_reports.routes import field_reports_bp
    app.register_blueprint(field_reports_bp, url_prefix="/api/field-reports")

    from app.violations.routes import violations_bp
    app.register_blueprint(violations_bp, url_prefix="/api/violations")

    from app.corrective_actions.routes import corrective_actions_bp
    app.register_blueprint(corrective_actions_bp, url_prefix="/api/corrective-actions")

    from app.incidents.routes import incidents_bp
    app.register_blueprint(incidents_bp, url_prefix="/api/incidents")

    from app.contractors.routes import contractors_bp
    app.register_blueprint(contractors_bp, url_prefix="/api/contractors")

    from app.documents.routes import documents_bp
    app.register_blueprint(documents_bp, url_prefix="/api/documents")

    from app.ai.routes import ai_bp
    app.register_blueprint(ai_bp, url_prefix="/api/ai")

    from app.workflow.routes import workflow_bp
    app.register_blueprint(workflow_bp, url_prefix="/api/rules")

    from app.gis.routes import gis_bp
    app.register_blueprint(gis_bp, url_prefix="/api/gis")

    from app.analytics.routes import analytics_bp
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

    from app.notifications.routes import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix="/api/notifications")

    from app.audit.routes import audit_bp
    app.register_blueprint(audit_bp, url_prefix="/api/audit-logs")

    from app.reports.routes import reports_bp
    app.register_blueprint(reports_bp, url_prefix="/api/reports")

    from app.rag.routes import rag_bp
    app.register_blueprint(rag_bp, url_prefix="/api/chat")

    # Web UI Page Routes
    from app.views import views_bp
    app.register_blueprint(views_bp)

    return app
