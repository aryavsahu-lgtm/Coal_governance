import json
from datetime import datetime, date
from bson import ObjectId
from flask import jsonify, make_response


class MongoJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle BSON ObjectId, datetime, and date objects."""

    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        return super().default(o)


def sanitize_doc(doc):
    """Recursively converts ObjectId and datetime to string/ISO format."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [sanitize_doc(item) for item in doc]
    if isinstance(doc, dict):
        sanitized = {}
        for key, value in doc.items():
            if key == "_id" and isinstance(value, ObjectId):
                sanitized["id"] = str(value)
                sanitized["_id"] = str(value)
            elif isinstance(value, ObjectId):
                sanitized[key] = str(value)
            elif isinstance(value, (datetime, date)):
                sanitized[key] = value.isoformat()
            elif isinstance(value, dict):
                sanitized[key] = sanitize_doc(value)
            elif isinstance(value, list):
                sanitized[key] = [sanitize_doc(item) for item in value]
            else:
                sanitized[key] = value
        return sanitized
    return doc


def success_response(data=None, message="Operation successful", status_code=200):
    """Standardized API success response envelope."""
    payload = {
        "success": True,
        "message": message,
        "data": sanitize_doc(data),
    }
    return make_response(jsonify(payload), status_code)


def error_response(code="INTERNAL_ERROR", message="An error occurred", status_code=500, details=None):
    """Standardized API error response envelope."""
    payload = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details:
        payload["error"]["details"] = details
    return make_response(jsonify(payload), status_code)
