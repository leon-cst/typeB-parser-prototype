"""
Domain models for the envelope layer: Address, CommReference,
RecordLocator, Envelope.

These are frozen (immutable) Pydantic models -- an envelope, once parsed,
shouldn't be mutated in place. If a transform is needed (e.g. building a
reply's envelope from a request's), build a new model with
`.model_copy(update={...})` rather than assigning to fields.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

# REQ03 p.9-10, "POS CONSTRUCTIONS": the 10 point-of-sale sub-fields, in
# the order the spec lists them. Fields 1-4 are described as mandatory,
# 5-10 as optional/conditional, but real traffic doesn't always include
# every field even when POS is present -- so a line can supply anywhere
# from 0 to 10 of these, in this fixed order, and any not present are
# left as None rather than guessed at.
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


class Address(BaseModel):
    """A single Type B address: 3-char city/airport code + 2-char office
    function code + 2-3 char airline/CRS designator.
    REQ03 section 2 (p.4) and section 4 "Communication Reference Element".

    Note: this is NOT the same shape as a record locator's "booking
    office" token (REQ03 p.9), which omits the office-function code
    entirely (city + airline/CRS only, slash-prefixed if 3 chars). See
    RecordLocator below for that shape.
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
    """Communication reference element: '.' + origin address + date/time
    group. REQ03 section 4 (p.6). Kept as a raw string for the date/time
    portion -- Type B's ddhhmm format has no month/year, so building a
    real datetime would mean guessing context we don't have here."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    origin: Address
    date_time_raw: str


class RecordLocator(BaseModel):
    """One record locator line: booking office + location of record,
    optionally followed by up to 10 slash-delimited point-of-sale (POS)
    sub-fields. REQ03 p.9-10, "RECORD LOCATOR ELEMENT" / "POS
    CONSTRUCTIONS".

    Shape: "<booking_office> <location_of_record>[/pos_field]*"
    e.g. "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU" (REQ03 p.49).

    `booking_office` and `location_of_record` are kept as raw strings,
    not further decomposed -- REQ03 doesn't give a fixed-width grammar
    for either (booking office is city/airport code + 2-3 char CRS/
    airline designator, but the designator length varies; location of
    record is a free-form PNR code) and Address.parse()'s shape doesn't
    apply here (see its docstring).

    POS sub-fields are filled strictly positionally, left to right: the
    Nth slash-delimited value found always maps to the Nth POS field
    (travel_agent_city_code, iata_number, city_airport_code, crs_code,
    user_type, iso_country_code, iso_currency_code, duty_code,
    user_id_pss, point_of_departure, in that order). Fields beyond
    however many values are present resolve to None. There is no
    attempt to detect or skip a field that's semantically "missing" in
    the middle of the sequence (e.g. a two-letter value landing in
    user_type, which REQ03 defines as single-letter A/E/N/T) -- nothing
    on the wire marks a field as skipped unless it's an explicit empty
    slash segment ("//"), so guessing at a shift would be exactly the
    kind of structural-ambiguity guess this project avoids. A field can
    only be absent by being omitted from the END of the line, matching
    REQ03's own "if POS is not available, still insert with slash"
    framing for trailing empties (see the BPR example's "/////" tail).
    """
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

        pos_values = loc_and_pos[1:]
        pos_fields = {
            name: (value.strip() or None)
            for name, value in zip(_POS_FIELD_NAMES, pos_values)
        }

        return cls(
            raw=raw,
            booking_office=booking_office,
            location_of_record=location_of_record,
            **pos_fields,
        )


class Envelope(BaseModel):
    """The parsed envelope: address block, communication reference,
    optional message identifier, optional record locator line(s).

    `record_locators` holds 0, 1 (primary only), or 2 (primary +
    secondary, REQ03 p.9's bilateral-agreement rule) RecordLocator
    entries, in the order they appeared on the wire.
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