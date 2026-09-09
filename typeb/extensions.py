"""Shared Flask extension instances.

Defined here (not in app.py) so both app.py and typeb/db/models.py can
import `db` without a circular import.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()