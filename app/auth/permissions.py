from functools import wraps
from flask import request
from app.auth.service import decode_access_token, get_user_by_id, ROLE_SUPER_ADMIN
from app.utils.responses import error_response


def require_jwt(f):
    """Decorator to enforce and decode Bearer JWT token."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return error_response(code="UNAUTHORIZED", message="Authorization header missing", status_code=401)
        
        parts = auth_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return error_response(code="UNAUTHORIZED", message="Invalid token format. Expected 'Bearer <token>'", status_code=401)
        
        token = parts[1]
        payload = decode_access_token(token)
        if not payload:
            return error_response(code="UNAUTHORIZED", message="Invalid or expired access token", status_code=401)
        
        user_id = payload.get("user_id")
        user = get_user_by_id(user_id)
        if not user or not user.get("is_active", True):
            return error_response(code="UNAUTHORIZED", message="User account deactivated or not found", status_code=401)
        
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def optional_jwt(f):
    """Decorator to decode Bearer JWT token if provided, or set request.current_user to None for public access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        request.current_user = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header:
            parts = auth_header.split(" ")
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                payload = decode_access_token(token)
                if payload:
                    user_id = payload.get("user_id")
                    user = get_user_by_id(user_id)
                    if user and user.get("is_active", True):
                        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function


def require_roles(*allowed_roles):
    """Decorator enforcing Role-Based Access Control (RBAC)."""
    def decorator(f):
        @wraps(f)
        @require_jwt
        def decorated_function(*args, **kwargs):
            user = getattr(request, "current_user", None)
            if not user:
                return error_response(code="UNAUTHORIZED", message="Authentication required", status_code=401)
            
            user_role = user.get("role")
            if user_role == ROLE_SUPER_ADMIN:
                return f(*args, **kwargs)
            
            if user_role not in allowed_roles:
                return error_response(
                    code="FORBIDDEN",
                    message=f"Access denied. Allowed roles: {', '.join(allowed_roles)}",
                    status_code=403
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_mine_access(user, mine_id):
    """Validates whether a user is allowed to access data for a given mine."""
    if not mine_id:
        return True
    user_role = user.get("role")
    if user_role in (ROLE_SUPER_ADMIN, "CORPORATE_MANAGEMENT", "REGULATORY_AUTHORITY"):
        return True
    user_mine_id = str(user.get("mine_id") or "")
    return user_mine_id == str(mine_id)
