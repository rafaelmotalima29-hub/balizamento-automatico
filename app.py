import os
from flask import Flask
from sqlalchemy import text
from config import Config
from extensions import db


def _migrate_db(db):
    """Add new columns to existing SQLite DB without losing data."""
    migrations = [
        "ALTER TABLE events ADD COLUMN num_corridas INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE results ADD COLUMN corrida_num INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE students ADD COLUMN classroom VARCHAR(20)",
        "ALTER TABLE events ADD COLUMN competition_group VARCHAR(50)",
        "ALTER TABLE events ADD COLUMN num_series INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE events ADD COLUMN athletes_per_series INTEGER NOT NULL DEFAULT 8",
    ]
    with db.engine.connect() as conn:
        for stmt in migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists — safe to ignore



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

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cadastros_bp)
    app.register_blueprint(balizamento_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(resultados_bp)

    # Create DB tables + migrate existing ones
    with app.app_context():
        db.create_all()
        _migrate_db(db)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
