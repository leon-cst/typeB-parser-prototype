"""
Domain models for the envelope layer: Address, CommReference, Envelope.

These are frozen (immutable) Pydantic models -- an envelope, once parsed,
shouldn't be mutated in place. If a transform is needed (e.g. building a
reply's envelope from a request's), build a new model with
`.model_copy(update={...})` rather than assigning to fields.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


class Address(BaseModel):
    """A single Type B address: 3-char city/airport code + 2-char office
    function code + 2-3 char airline/CRS designator.
    REQ03 section 2 (p.4) and section 4 "Communication Reference Element".

    Note: this is NOT the same shape as a record locator's "booking
    office" token (REQ03 p.9), which omits the office-function code
    entirely (city + airline/CRS only, slash-prefixed if 3 chars). Record
    locators are kept as lightweight raw strings for now -- see
    RecordLocator below -- rather than modeled with this class.
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


class Envelope(BaseModel):
    """The parsed envelope: address block, communication reference,
    optional message identifier, optional record locator line(s).

    `record_locator_lines` is intentionally a list of raw strings, not a
    structured model, for now. REQ03 p.9-10 describes a fairly involved
    record locator grammar (primary + secondary, POS construction with
    up to 10 bilateral-agreement-dependent sub-fields) that isn't needed
    to get envelope *structure* right, and modeling it prematurely risks
    guessing at fields we haven't seen enough real examples to be sure
    of. Structured record-locator parsing is a good candidate for its
    own later step once we have more real (not just spec-worked-example)
    samples to validate against.
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    priority_code: str
    addresses: list[Address]
    comm_reference: CommReference
    message_identifier: str | None
    record_locator_lines: list[str]

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
