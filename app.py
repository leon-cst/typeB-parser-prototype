"""
Type B Parser -- application factory.

Route logic lives in typeb/web/api.py (existing parser/reply endpoints)
and, going forward, typeb/web/dashboard.py (agreement-table CRUD GUI).
This file only assembles the app: config, extensions, blueprints.
"""
import os

from dotenv import load_dotenv
from flask import Flask
from flask_migrate import Migrate

from typeb.extensions import db
from typeb.web.api import api_bp
from typeb.web.dashboard import dashboard_bp

# Import so Flask-Migrate's autogenerate can discover the ORM models.
# Unused directly here, but the import has the side effect of
# registering Agreement with db.Model's metadata.
from typeb.db import models as _models  # noqa: F401

load_dotenv()


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "")
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-later")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    Migrate(app, db)

    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)