import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "natacao-balizamento-2025")
    # Database configuration: Use DATABASE_URL from environment (production) or SQLite (local)
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "swimming.db"))
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    if "VERCEL" in os.environ:
        UPLOAD_FOLDER = "/tmp/uploads"
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
