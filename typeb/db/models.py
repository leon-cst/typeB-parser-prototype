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


class Pnr(db.Model):
    __tablename__ = "PNR"

    PNR_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)

    PNR_Code = db.Column(db.String(10), nullable=False, index=True)

    Booking_Office_Code = db.Column(db.String(10), nullable=False)
    POS_Travel_Agent_ID = db.Column(db.String(20), nullable=True)
    POS_City_Code = db.Column(db.String(3), nullable=True)
    POS_User_Type = db.Column(db.String(5), nullable=True)
    Creation_Date = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    source = db.Column(db.String(10), nullable=False, default="manual")

    def __repr__(self) -> str:
        return f"<Pnr {self.PNR_ID} code={self.PNR_Code!r}>"


class Passenger(db.Model):
    __tablename__ = "PASSENGER"

    Passenger_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)

    PNR_ID = db.Column(
        db.Integer,
        db.ForeignKey("PNR.PNR_ID", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    Family_Name = db.Column(db.String(50), nullable=False)
    First_Name_Middle_Name = db.Column(db.String(100), nullable=True)
    Title = db.Column(db.String(10), nullable=True)
    Number_In_Party = db.Column(db.Integer, nullable=True)

    Passenger_Type = db.Column(db.String(5), nullable=True)
    Email = db.Column(db.String(255), nullable=True)
    Date_Of_Birth_Raw = db.Column(db.String(10), nullable=True)
    Foid = db.Column(db.String(50), nullable=True)

    pnr = db.relationship("Pnr", backref=db.backref("passengers", cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<Passenger {self.Passenger_ID} {self.Family_Name!r}>"


class FlightSegment(db.Model):
    __tablename__ = "FLIGHT_SEGMENT"

    Segment_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)

    PNR_ID = db.Column(
        db.Integer,
        db.ForeignKey("PNR.PNR_ID", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    Airline_Code = db.Column(db.String(3), nullable=True)
    Flight_Number = db.Column(db.String(10), nullable=False)
    RBD_Class = db.Column(db.String(1), nullable=True)
    Flight_Date = db.Column(db.Date, nullable=True)  # nullable now -- see Flight_Date_Raw
    Flight_Date_Raw = db.Column(db.String(7), nullable=True)  # ddMMM, true source (no year)
    Boarding_Point = db.Column(db.String(3), nullable=False)
    Off_Point = db.Column(db.String(3), nullable=False)
    Action_Code = db.Column(db.String(2), nullable=True)
    Number_In_Party = db.Column(db.Integer, nullable=True)
    Departure_Time = db.Column(db.Time, nullable=True)
    Arrival_Time = db.Column(db.Time, nullable=True)
    Arrival_Day_Offset = db.Column(db.SmallInteger, nullable=True)

    pnr = db.relationship("Pnr", backref=db.backref("flight_segments", cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return (
            f"<FlightSegment {self.Segment_ID} {self.Flight_Number} "
            f"{self.Flight_Date_Raw or self.Flight_Date} "
            f"{self.Boarding_Point}-{self.Off_Point}>"
        )


class Osi(db.Model):
    __tablename__ = "OSI"

    OSI_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)

    PNR_ID = db.Column(
        db.Integer,
        db.ForeignKey("PNR.PNR_ID", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    Airline_Code = db.Column(db.String(3), nullable=False)
    Information_Text = db.Column(db.String(255), nullable=False)

    pnr = db.relationship("Pnr", backref=db.backref("osi_entries", cascade="all, delete-orphan"))

    def __repr__(self) -> str:
        return f"<Osi {self.OSI_ID} {self.Airline_Code!r}>"


class Ssr(db.Model):
    __tablename__ = "SSR"

    SSR_ID = db.Column(db.Integer, primary_key=True, autoincrement=True)

    PNR_ID = db.Column(
        db.Integer,
        db.ForeignKey("PNR.PNR_ID", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    Passenger_ID = db.Column(
        db.Integer,
        db.ForeignKey("PASSENGER.Passenger_ID", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )

    Segment_ID = db.Column(
        db.Integer,
        db.ForeignKey("FLIGHT_SEGMENT.Segment_ID", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )

    SSR_Code = db.Column(db.String(4), nullable=False)
    Airline_Code = db.Column(db.String(3), nullable=True)
    Action_Code = db.Column(db.String(2), nullable=True)
    Free_Text = db.Column(db.String(255), nullable=True)

    pnr = db.relationship("Pnr", backref=db.backref("ssr_entries", cascade="all, delete-orphan"))
    passenger = db.relationship("Passenger", backref="ssr_entries")
    segment = db.relationship("FlightSegment", backref="ssr_entries")

    def __repr__(self) -> str:
        return f"<Ssr {self.SSR_ID} {self.SSR_Code!r}>"