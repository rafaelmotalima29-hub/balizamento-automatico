import os
from flask import Flask
from sqlalchemy import text
from config import Config
from extensions import db


_DEFAULT_SCORE_CONFIG = {1: 10, 2: 8, 3: 7, 4: 6, 5: 5, 6: 4, 7: 3, 8: 2, 9: 1}


def _migrate_db(db):
    """
    Safely add new columns to existing tables without losing data.
    Works for both SQLite and PostgreSQL.

    On PostgreSQL, a failed statement inside a transaction puts the connection
    in an aborted state — all subsequent commands also fail silently unless we
    rollback explicitly after each failure.
    """
    # (table, column, definition)
    columns_to_add = [
        ("events",   "num_corridas",       "INTEGER NOT NULL DEFAULT 1"),
        ("results",  "corrida_num",         "INTEGER NOT NULL DEFAULT 1"),
        ("students", "classroom",           "VARCHAR(20)"),
        ("events",   "competition_group",   "VARCHAR(50)"),
        ("events",   "num_series",          "INTEGER NOT NULL DEFAULT 1"),
        ("events",   "athletes_per_series", "INTEGER NOT NULL DEFAULT 8"),
    ]

    is_postgres = "postgresql" in db.engine.url.drivername

    with db.engine.connect() as conn:
        for table, column, definition in columns_to_add:
            # Check if column already exists (avoids error entirely)
            if is_postgres:
                exists_query = text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                )
                row = conn.execute(exists_query, {"t": table, "c": column}).fetchone()
            else:
                # SQLite: PRAGMA table_info
                row = conn.execute(
                    text(f"PRAGMA table_info({table})")
                ).fetchall()
                row = next((r for r in row if r[1] == column), None)

            if row:
                continue  # Column already exists — skip

            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
                conn.commit()
            except Exception as exc:
                # Rollback so the connection is usable for the next column
                try:
                    conn.rollback()
                except Exception:
                    pass


def _seed_score_config(db):
    """Insere a pontuação padrão se a tabela estiver vazia."""
    from models import ScoreConfig
    if ScoreConfig.query.count() == 0:
        for placement, points in _DEFAULT_SCORE_CONFIG.items():
            db.session.add(ScoreConfig(placement=placement, points=points))
        db.session.commit()




def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from routes.dashboard import dashboard_bp
    from routes.cadastros import cadastros_bp
    from routes.balizamento import balizamento_bp
    from routes.upload import upload_bp
    from routes.resultados import resultados_bp
    from routes.cancelamentos import cancelamentos_bp
    from routes.pontuacao import pontuacao_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cadastros_bp)
    app.register_blueprint(balizamento_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(resultados_bp)
    app.register_blueprint(cancelamentos_bp)
    app.register_blueprint(pontuacao_bp)

    # Create DB tables + migrate existing ones + seed defaults
    with app.app_context():
        db.create_all()
        _migrate_db(db)
        _seed_score_config(db)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
