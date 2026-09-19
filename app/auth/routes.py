from datetime import datetime
from flask import Blueprint, request
from bson import ObjectId

from app.auth.service import (
    authenticate_user,
    generate_access_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    ROLE_SUPER_ADMIN,
    ALL_ROLES
)
from app.auth.permissions import require_jwt, require_roles
from app.database import mongo
from app.utils.responses import success_response, error_response

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return error_response(code="VALIDATION_ERROR", message="Email and password are required", status_code=400)

    user = authenticate_user(email, password)
    if not user:
        return error_response(code="INVALID_CREDENTIALS", message="Invalid email or password", status_code=401)

    token = generate_access_token(user)
    
    # Exclude password_hash from response
    user_data = dict(user)
    user_data.pop("password_hash", None)

    return success_response(
        data={
            "token": token,
            "user": user_data
        },
        message="Login successful"
    )


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    role = data.get("role", "CONTRACTOR")

    if not email or not password or not name:
        return error_response(code="VALIDATION_ERROR", message="Email, password, and name are required", status_code=400)

    if role not in ALL_ROLES:
        return error_response(code="VALIDATION_ERROR", message=f"Invalid role. Must be one of: {', '.join(ALL_ROLES)}", status_code=400)

    # If registering non-contractor, check if authenticated as SUPER_ADMIN
    if role != "CONTRACTOR":
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return error_response(code="FORBIDDEN", message="Only Super Admin can register internal officer roles", status_code=403)

    if get_user_by_email(email):
        return error_response(code="CONFLICT", message="User with this email already exists", status_code=409)

    user = create_user(data)
    return success_response(data=user, message="User registered successfully", status_code=201)


@auth_bp.route("/me", methods=["GET"])
@require_jwt
def me():
    user = dict(request.current_user)
    user.pop("password_hash", None)
    return success_response(data=user, message="Profile retrieved")


@auth_bp.route("/logout", methods=["POST"])
@require_jwt
def logout():
    return success_response(data=None, message="Logged out successfully")


@auth_bp.route("/users", methods=["GET"])
@require_roles(ROLE_SUPER_ADMIN, "CORPORATE_MANAGEMENT")
def list_users():
    role_filter = request.args.get("role")
    query = {}
    if role_filter:
        query["role"] = role_filter
    
    cursor = mongo.users.find(query)
    users = []
    for u in cursor:
        u_dict = dict(u)
        u_dict.pop("password_hash", None)
        users.append(u_dict)

    return success_response(data=users, message="Users retrieved successfully")


@auth_bp.route("/users/<user_id>/status", methods=["PUT"])
@require_roles(ROLE_SUPER_ADMIN)
def toggle_user_status(user_id):
    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")
    if is_active is None:
        return error_response(code="VALIDATION_ERROR", message="'is_active' boolean field required", status_code=400)

    query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
    result = mongo.users.update_one(query, {"$set": {"is_active": bool(is_active), "updated_at": datetime.utcnow()}})
    
    if result.matched_count == 0:
        return error_response(code="NOT_FOUND", message="User not found", status_code=404)

    return success_response(data={"user_id": user_id, "is_active": bool(is_active)}, message="User status updated")


@auth_bp.route("/password-reset", methods=["POST"])
def password_reset():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    new_password = data.get("new_password", "")

    if not email or not new_password:
        return error_response(code="VALIDATION_ERROR", message="Email and new_password are required", status_code=400)

    user = get_user_by_email(email)
    if not user:
        return error_response(code="NOT_FOUND", message="No user registered with this email", status_code=404)

    hashed = hash_password(new_password)
    mongo.users.update_one({"email": email}, {"$set": {"password_hash": hashed, "updated_at": datetime.utcnow()}})

    return success_response(data=None, message="Password has been reset successfully")
