import os
import sys
from sqlalchemy.pool import NullPool

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

_IS_VERCEL = "VERCEL" in os.environ


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "natacao-balizamento-2025")

    # Database configuration: Use DATABASE_URL from environment (production) or SQLite (local)
    _db_url = os.environ.get("DATABASE_URL", "sqlite:///" + os.path.join(BASE_DIR, "swimming.db"))
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)

    # Supabase pooler (port 6543) needs ?options=... to work with
    # Transaction Mode. Ensure prepare_threshold is disabled.
    if ":6543/" in _db_url and "prepare_threshold" not in _db_url:
        sep = "&" if "?" in _db_url else "?"
        _db_url += f"{sep}prepared_statement_cache_size=0"

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if _IS_VERCEL:
        # Log the DB host (never the password) to help debug connection issues
        try:
            from urllib.parse import urlparse
            _parsed = urlparse(_db_url)
            print(f"[SwimRank] DB host={_parsed.hostname} port={_parsed.port} user={_parsed.username}", file=sys.stderr)
        except Exception:
            pass

        # Serverless: NullPool evita conexões presas entre invocações;
        # sslmode=require é necessário para o Supabase.
        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": NullPool,
            "connect_args": {"sslmode": "require"},
        }
        UPLOAD_FOLDER = "/tmp/uploads"
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
        UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
