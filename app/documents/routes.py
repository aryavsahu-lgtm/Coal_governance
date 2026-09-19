import os
from flask import Blueprint, request, send_file, Response
from app.auth.permissions import require_jwt, optional_jwt, require_roles, check_mine_access
from app.auth.service import ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER, ROLE_ENVIRONMENTAL_OFFICER, ROLE_CONTRACTOR
from app.storage import storage_service
from app.documents.service import (
    save_document_record,
    list_documents,
    get_document_by_id,
    scan_and_update_document_expiries
)
from app.config import Config
from app.utils.responses import success_response, error_response

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/upload", methods=["POST"])
@require_jwt
def upload_document():
    if "file" not in request.files:
        return error_response(code="VALIDATION_ERROR", message="No file part in request", status_code=400)
    
    file = request.files["file"]
    if not file or file.filename == "":
        return error_response(code="VALIDATION_ERROR", message="No file selected", status_code=400)

    mine_id = request.form.get("mine_id")
    if not mine_id:
        return error_response(code="VALIDATION_ERROR", message="mine_id is required", status_code=400)

    user = request.current_user
    if not check_mine_access(user, mine_id):
        return error_response(code="FORBIDDEN", message="Unauthorized for this mine", status_code=403)

    doc_type = request.form.get("document_type", "STATUTORY_CLEARANCE")

    # Upload using StorageService abstraction
    upload_res = storage_service.upload(file, filename=file.filename, subfolder="documents")

    # Optional manual overrides
    manual_overrides = {
        "document_number": request.form.get("document_number"),
        "authority": request.form.get("authority"),
        "issue_date": request.form.get("issue_date"),
        "expiry_date": request.form.get("expiry_date")
    }

    doc_record = save_document_record(
        file_meta=upload_res,
        document_type=doc_type,
        mine_id=mine_id,
        user=user,
        manual_override=manual_overrides
    )

    return success_response(data=doc_record, message="Document uploaded and OCR processed", status_code=201)


@documents_bp.route("", methods=["GET"])
@optional_jwt
def get_all():
    user = getattr(request, "current_user", None)
    mine_id = request.args.get("mine_id")
    doc_type = request.args.get("document_type")
    status = request.args.get("status")

    if user and user.get("role") in ("MINE_OFFICER", "SAFETY_OFFICER", "ENVIRONMENTAL_OFFICER"):
        user_mine = str(user.get("mine_id") or "")
        if user_mine:
            mine_id = user_mine

    docs = list_documents(mine_id=mine_id, doc_type=doc_type, status=status)
    return success_response(data=docs, message="Documents retrieved")


@documents_bp.route("/<doc_id>", methods=["GET"])
@require_jwt
def get_one(doc_id):
    doc = get_document_by_id(doc_id)
    if not doc:
        return error_response(code="NOT_FOUND", message="Document not found", status_code=404)
    return success_response(data=doc, message="Document details")


@documents_bp.route("/scan-expiries", methods=["POST"])
@require_roles(ROLE_SUPER_ADMIN, ROLE_MINE_OFFICER, ROLE_SAFETY_OFFICER)
def scan_expiries():
    result = scan_and_update_document_expiries()
    return success_response(data=result, message="Document expiry scan completed")


@documents_bp.route("/file/<path:subpath>", methods=["GET"])
def serve_stored_file(subpath):
    """Securely serve uploaded media/documents."""
    full_path = Config.UPLOAD_FOLDER / subpath.replace("/", os.sep)
    if not full_path.exists() or not full_path.is_file():
        return error_response(code="NOT_FOUND", message="File not found", status_code=404)
    return send_file(str(full_path))
