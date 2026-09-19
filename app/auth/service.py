import datetime
import logging
from typing import Optional, Dict, Any
from bson import ObjectId
import bcrypt
import jwt
from app.config import Config
from app.database import mongo

logger = logging.getLogger("coal_governance.auth")

ROLE_SUPER_ADMIN = "SUPER_ADMIN"
ROLE_CORPORATE_MANAGEMENT = "CORPORATE_MANAGEMENT"
ROLE_MINE_OFFICER = "MINE_OFFICER"
ROLE_SAFETY_OFFICER = "SAFETY_OFFICER"
ROLE_INSPECTION_OFFICER = "INSPECTION_OFFICER"
ROLE_ENVIRONMENTAL_OFFICER = "ENVIRONMENTAL_OFFICER"
ROLE_CONTRACTOR = "CONTRACTOR"
ROLE_REGULATORY_AUTHORITY = "REGULATORY_AUTHORITY"

ALL_ROLES = [
    ROLE_SUPER_ADMIN,
    ROLE_CORPORATE_MANAGEMENT,
    ROLE_MINE_OFFICER,
    ROLE_SAFETY_OFFICER,
    ROLE_INSPECTION_OFFICER,
    ROLE_ENVIRONMENTAL_OFFICER,
    ROLE_CONTRACTOR,
    ROLE_REGULATORY_AUTHORITY,
]


def hash_password(password: str) -> str:
    """Securely hash a password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_access_token(user: Dict[str, Any]) -> str:
    """Generate JWT access token containing identity and role claims."""
    now = datetime.datetime.utcnow()
    expires_at = now + datetime.timedelta(minutes=Config.JWT_ACCESS_TOKEN_EXPIRES_MINUTES)
    
    payload = {
        "sub": str(user.get("_id", "")),
        "user_id": str(user.get("_id", "")),
        "email": user.get("email"),
        "name": user.get("name"),
        "role": user.get("role"),
        "subsidiary_id": str(user.get("subsidiary_id", "")),
        "mine_id": str(user.get("mine_id", "")),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp())
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.info("JWT access token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        return None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch user by string ID or ObjectId."""
    try:
        query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
        return mongo.users.find_one(query)
    except Exception as e:
        logger.error(f"Error fetching user by id {user_id}: {e}")
        return None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch user by email (case-insensitive)."""
    return mongo.users.find_one({"email": email.strip().lower()})


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Verify credentials and return user dict if active."""
    user = get_user_by_email(email)
    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


def create_user(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new user with hashed password."""
    now = datetime.datetime.utcnow()
    user_doc = {
        "email": data["email"].strip().lower(),
        "password_hash": hash_password(data["password"]),
        "name": data.get("name", "").strip(),
        "role": data.get("role", ROLE_MINE_OFFICER),
        "subsidiary_id": data.get("subsidiary_id"),
        "mine_id": data.get("mine_id"),
        "phone": data.get("phone", ""),
        "designation": data.get("designation", ""),
        "is_active": data.get("is_active", True),
        "created_at": now,
        "updated_at": now
    }
    res = mongo.users.insert_one(user_doc)
    user_doc["_id"] = res.inserted_id
    user_doc.pop("password_hash", None)
    return user_doc
