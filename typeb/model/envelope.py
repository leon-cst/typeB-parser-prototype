from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

_POS_FIELD_NAMES = (
    "travel_agent_city_code",
    "iata_number",
    "city_airport_code",
    "crs_code",
    "user_type",
    "iso_country_code",
    "iso_currency_code",
    "duty_code",
    "user_id_pss",
    "point_of_departure",
)

_USER_TYPE_INDEX = _POS_FIELD_NAMES.index("user_type")

# REQ03 p.9-10 enumerates user type as exactly these single letters.
_VALID_USER_TYPES = {"A", "E", "N", "T"}


class Address(BaseModel):
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
            raise ValueError(f"Address token missing airline/CRS designator: {token!r}")
        return cls(raw=cleaned, city_code=city_code, office_code=office_code, designator=designator)


class CommReference(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    origin: Address
    date_time_raw: str


class RecordLocator(BaseModel):
    """REQ03 p.9-10: '<booking_office> <location_of_record>[/pos_field]*'.

    booking_office itself is "<3-char city/airport code><airline
    designator>" (REQ03 section 6: "3 digit city or airport code +
    Airline designator atau CRS originating message") -- same shape as
    Address, so it's decomposed the same way. A 3-character designator
    is written with a '/' separator instead ("DPS/ABC" per REQ03's own
    example); booking_office_designator strips that slash if present.

    POS fields fill positionally, except that a 5th value which isn't a
    valid user type (A/E/N/T) is treated as user_type being omitted
    without a placeholder slash, and shifts the remaining values down.
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    booking_office: str
    booking_office_city: str
    booking_office_designator: str
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

        if "/" in booking_office:
            # REQ03 section 6: a 3-character airline designator is
            # written with a '/' separator, e.g. "DPS/ABC".
            booking_office_city, _, booking_office_designator = booking_office.partition("/")
        else:
            booking_office_city, booking_office_designator = (
                booking_office[:3],
                booking_office[3:],
            )
        if len(booking_office_city) != 3 or not booking_office_designator:
            raise ValueError(
                f"Booking office doesn't match '<3-char city code>"
                f"<designator>' (REQ03 section 6): {booking_office!r} "
                f"in {line!r}"
            )

        rest = rest.strip()
        if not rest:
            raise ValueError(f"Record locator line missing location of record: {line!r}")

        loc_and_pos = rest.split("/")
        location_of_record = loc_and_pos[0].strip()
        if not location_of_record:
            raise ValueError(f"Record locator line missing location of record: {line!r}")

        pos_values = [v.strip() or None for v in loc_and_pos[1:]]

        # user_type omitted without a placeholder slash -- see class docstring.
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
            booking_office_city=booking_office_city,
            booking_office_designator=booking_office_designator,
            location_of_record=location_of_record,
            **pos_fields,
        )


class Envelope(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    priority_code: str
    addresses: list[Address]
    comm_reference: CommReference
    message_identifier: str | None
    record_locators: list[RecordLocator]

    @field_validator("addresses")
    @classmethod
    def _at_least_one_address(cls, v):
        if not v:
            raise ValueError("Envelope must have at least one address")
        return v

    @property
    def effective_identifier(self) -> str:
        return self.message_identifier or "BOOKING"