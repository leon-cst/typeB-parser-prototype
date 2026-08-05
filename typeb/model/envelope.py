"""
Domain models for the envelope layer: Address, CommReference,
RecordLocator, Envelope.

"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

# REQ03 p.9-10, "POS CONSTRUCTIONS": the 10 point-of-sale sub-fields, in
# the order the spec lists them. Order is currently fixed (which could mean incorrect)
# Confirm, then revisit and fix.
_POS_FIELD_NAMES = (
    "travel_agent_city_code",  # 1: in-house travel agent / TA city code
    "iata_number",             # 2: travel agent user ID (IATA) number
    "city_airport_code",       # 3: city/airport code, e.g. "JKT"
    "crs_code",                # 4: CRS code, e.g. "LH"
    "user_type",               # 5: A=Airlines, E=ERSP, N=no user ID, T=other
    "iso_country_code",        # 6: ISO country code, e.g. "ID"
    "iso_currency_code",       # 7: ISO currency code for ticket payment
    "duty_code",                # 8: duty code of agent, e.g. "SU"
    "user_id_pss",              # 9: user ID within the PSS
    "point_of_departure",       # 10: point of departure, e.g. "CGK"
)

_USER_TYPE_INDEX = _POS_FIELD_NAMES.index("user_type")

# EXPAND as needed
_VALID_USER_TYPES = {"A", "E", "N", "T"}


class Address(BaseModel):
    """A single Type B address: 3-char city/airport code + 2-char office
    function code + 2-3 char airline/CRS designator.
    REQ03 section 2 (p.4) and section 4 "Communication Reference Element".

    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    city_code: str
    office_code: str
    designator: str

    @classmethod
    def parse(cls, token: str) -> "Address":
        cleaned = token.strip()
        if len(cleaned) < 6:
            raise ValueError(f"Address token too short: {token!r}")
        city_code, office_code, designator = cleaned[:3], cleaned[3:5], cleaned[5:]
        if not designator:
            raise ValueError(
                f"Address token missing airline/CRS designator: {token!r}"
            )
        return cls(
            raw=cleaned,
            city_code=city_code,
            office_code=office_code,
            designator=designator,
        )


class CommReference(BaseModel):
    """Communication reference element: '.' + origin address + date/time group."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    origin: Address
    date_time_raw: str


class RecordLocator(BaseModel):
    """One record locator line"""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    booking_office: str
    location_of_record: str
    travel_agent_city_code: str | None = None
    iata_number: str | None = None
    city_airport_code: str | None = None
    crs_code: str | None = None
    user_type: str | None = None
    iso_country_code: str | None = None
    iso_currency_code: str | None = None
    duty_code: str | None = None
    user_id_pss: str | None = None
    point_of_departure: str | None = None

    @classmethod
    def parse(cls, line: str) -> "RecordLocator":
        raw = line.strip()
        head, sep, rest = raw.partition(" ")
        if not sep:
            raise ValueError(
                f"Record locator line missing booking office / location "
                f"of record separator (expected a space): {line!r}"
            )
        booking_office = head.strip()
        if not booking_office:
            raise ValueError(f"Record locator line missing booking office: {line!r}")

        rest = rest.strip()
        if not rest:
            raise ValueError(
                f"Record locator line missing location of record: {line!r}"
            )

        # rest = "<location_of_record>[/pos_field]*"
        loc_and_pos = rest.split("/")
        location_of_record = loc_and_pos[0].strip()
        if not location_of_record:
            raise ValueError(
                f"Record locator line missing location of record: {line!r}"
            )

        pos_values = [v.strip() or None for v in loc_and_pos[1:]]
 
        # user_type omitted without a placeholder slash
        if (
            len(pos_values) > _USER_TYPE_INDEX
            and pos_values[_USER_TYPE_INDEX] is not None
            and pos_values[_USER_TYPE_INDEX] not in _VALID_USER_TYPES
        ):
            pos_values.insert(_USER_TYPE_INDEX, None)
 
        pos_fields = dict(zip(_POS_FIELD_NAMES, pos_values))


        return cls(
            raw=raw,
            booking_office=booking_office,
            location_of_record=location_of_record,
            **pos_fields,
        )


class Envelope(BaseModel):
    """The parsed envelope: address block, communication reference,
    optional message identifier, optional record locator line(s).

    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    priority_code: str
    addresses: list[Address]
    comm_reference: CommReference
    message_identifier: str | None
    record_locators: list[RecordLocator]

    @field_validator("addresses")
    @classmethod
    def _at_least_one_address(cls, v: list[Address]) -> list[Address]:
        if not v:
            raise ValueError("Envelope must have at least one address")
        return v

    @property
    def effective_identifier(self) -> str:
        """message_identifier, or the synthetic 'BOOKING' pseudo-identifier
        when none is present (REQ03 section 5's implicit-booking rule)."""
        return self.message_identifier or "BOOKING"