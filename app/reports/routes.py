from flask import Blueprint, request, Response
from app.auth.permissions import require_jwt
from app.reports.generator import generate_csv_report, generate_pdf_report
from app.utils.responses import error_response

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/download", methods=["GET"])
@require_jwt
def download_report():
    report_type = request.args.get("type", "monthly").lower()
    report_format = request.args.get("format", "csv").lower()
    mine_id = request.args.get("mine_id")

    if report_format == "pdf":
        try:
            pdf_bytes, filename = generate_pdf_report(report_type, mine_id=mine_id)
            return Response(
                pdf_bytes,
                mimetype="application/pdf",
                headers={"Content-Disposition": f"attachment;filename={filename}"}
            )
        except Exception as e:
            return error_response(code="PDF_GENERATION_ERROR", message=str(e), status_code=500)

    elif report_format == "csv":
        csv_data, filename = generate_csv_report(report_type, mine_id=mine_id)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    return error_response(code="VALIDATION_ERROR", message="Invalid format. Supported: csv, pdf", status_code=400)
