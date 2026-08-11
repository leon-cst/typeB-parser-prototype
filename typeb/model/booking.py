from __future__ import annotations
from pydantic import BaseModel, ConfigDict

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import (
    NameElement,
    OsiContactAddressElement,
    SegmentElement,
    SsrGroupFareElement,
    SsrGroupSeatElement,
)
from typeb.model.envelope import Envelope
from typeb.model.passenger import BookingPassenger


class GroupPlaceholder(BaseModel):
    """A NAME element with no individual names given (REQ03 section 7),
    e.g. "6SEAMEN" or "30SITA/TOUR". confirmed_party_size comes from a
    matching SSR GRPS line's TCP value when present."""
    model_config = ConfigDict(frozen=True)

    surname: str
    number_in_party: int
    group_name_suffix: str | None
    confirmed_party_size: int | None = None


class BookingMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    passengers: list[BookingPassenger]
    name_elements: list[NameElement]
    group_placeholders: list[GroupPlaceholder]
    arrival_elements: list[SegmentElement]
    segments: list[SegmentElement]
    airline_record_locators: list[str]
    group_fare_info: list[SsrGroupFareElement]
    group_seat_requests: list[SsrGroupSeatElement]
    contact_addresses: list[OsiContactAddressElement]
    warnings: list[str]
    unrecognized_lines: list[UnrecognizedLine]