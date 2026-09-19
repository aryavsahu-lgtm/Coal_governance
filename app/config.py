import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


class Config:
    """Centralized Application Configuration"""

    # Secret & App Mode
    SECRET_KEY = os.getenv("SECRET_KEY", "coal-mine-governance-secret-key-production-ready")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")
    PORT = int(os.getenv("PORT", 5000))

    # MongoDB Configuration
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "coal_governance")

    # JWT Authentication
    JWT_SECRET = os.getenv("JWT_SECRET", "coal_gov_super_secret_jwt_key_dgms_compliance_2026_x89a1")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", 480))

    # File Uploads
    UPLOAD_FOLDER = BASE_DIR / os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", 16 * 1024 * 1024))  # 16 MB
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf", "mp4", "avi", "csv", "xlsx"}

    # AI & Computer Vision
    ENABLE_MOCK_AI = os.getenv("ENABLE_MOCK_AI", "true").lower() in ("1", "true", "yes")
    YOLO_MODEL_PATH = BASE_DIR / os.getenv("YOLO_MODEL_PATH", "models/yolov8n.pt")
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.45))
    OCR_ENGINE = os.getenv("OCR_ENGINE", "fallback")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def ensure_directories(cls):
        """Ensure necessary working directories exist"""
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "models").mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
