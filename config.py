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

    # Strip invalid psycopg2 param that may have been appended in prior versions
    if "prepared_statement_cache_size" in _db_url:
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
        _p = urlparse(_db_url)
        _qs = {k: v for k, v in parse_qs(_p.query).items() if k != "prepared_statement_cache_size"}
        _db_url = urlunparse(_p._replace(query=urlencode(_qs, doseq=True)))

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if _IS_VERCEL:
        # Log the DB host (never the password) to help debug connection issues
        try:
            from urllib.parse import urlparse as _urlparse
            _parsed = _urlparse(_db_url)
            print(f"[SwimRank] DB host={_parsed.hostname} port={_parsed.port} user={_parsed.username}", file=sys.stderr)
        except Exception:
            pass

        # Serverless: NullPool evita conexões presas entre invocações;
        # sslmode=require é necessário para o Supabase.
        # prepare_threshold=0 disables prepared statements (required for pgbouncer/pooler).
        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": NullPool,
            "connect_args": {
                "sslmode": "require",
                "options": "-c statement_timeout=30000",
            },
        }
        UPLOAD_FOLDER = "/tmp/uploads"
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
        UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}
