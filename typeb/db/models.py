"""
SQLAlchemy ORM models -- storage layer only.

Deliberately separate from typeb/model/ (the Pydantic parser models).
Column types are kept generic (String, Integer, Boolean, DateTime) so
the schema can migrate off MariaDB later without rewriting models.
"""
from datetime import datetime, timezone

from typeb.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agreement(db.Model):
    __tablename__ = "AGREEMENT_TABLE"

    Agreement_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)

    Partner_Code = db.Column(db.String(10), nullable=False)

    # Free-text for now -- valid value list pending confirmation from
    # Parka. Tighten to an Enum/CHECK constraint once confirmed.
    Response_Format_Option = db.Column(db.String(50), nullable=True)

    # Free-text for now -- exact format (single date vs range vs rule)
    # pending confirmation from Parka.
    Allowed_Dates = db.Column(db.String(50), nullable=True)

    # Comma-separated city pairs for now. Revisit as a child table if
    # per-route validation/lookup is needed later.
    Allowed_Routes = db.Column(db.String(255), nullable=True)

    # --- Audit columns (not in the original schema doc, added here) ---
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
    updated_by = db.Column(db.String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<Agreement {self.Agreement_ID} partner={self.Partner_Code!r}>"


class MessageIdentifier(db.Model):
    __tablename__ = "MESSAGE_IDENTIFIER"

    Msg_Identifier_Code = db.Column(db.String(3), primary_key=True)
    Description = db.Column(db.String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<MessageIdentifier {self.Msg_Identifier_Code!r}>"


class InventoryAvailability(db.Model):
    __tablename__ = "INVENTORY_AVAILABILITY"

    Inventory_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Flight_Number = db.Column(db.String(10), nullable=False)
    Flight_Date = db.Column(db.Date, nullable=False)
    Boarding_Point = db.Column(db.String(3), nullable=False)
    Off_Point = db.Column(db.String(3), nullable=False)
    RBD_Class = db.Column(db.String(1), nullable=False)
    Segment_Status_Code = db.Column(db.String(5), nullable=True)
    Numeric_Availability = db.Column(db.String(10), nullable=True)

    source = db.Column(db.String(10), nullable=False, default="manual")

    def __repr__(self) -> str:
        return (
            f"<InventoryAvailability {self.Flight_Number} "
            f"{self.Flight_Date} {self.Boarding_Point}-{self.Off_Point} "
            f"{self.RBD_Class}>"
        )