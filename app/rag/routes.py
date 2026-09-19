from flask import Blueprint, request
from app.auth.permissions import optional_jwt
from app.rag.chatbot import generate_rag_response
from app.utils.responses import success_response, error_response

rag_bp = Blueprint("chat", __name__)


@rag_bp.route("", methods=["POST"])
@optional_jwt
def chat_query():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return error_response(code="VALIDATION_ERROR", message="Message field is required", status_code=400)

    result = generate_rag_response(message)
    return success_response(data=result, message="Query answered with regulatory citations")
