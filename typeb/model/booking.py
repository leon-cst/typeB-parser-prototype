"""
Output model for a fully assembled booking message -- see
typeb.messages.booking for the function that builds these.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import NameElement, SegmentElement
from typeb.model.envelope import Envelope
from typeb.model.passenger import BookingPassenger


class BookingMessage(BaseModel):
    """A fully parsed and cross-referenced booking message: envelope,
    every passenger with their merged contact/status info, every flight
    segment, any non-fatal validation warnings, and anything that
    couldn't be handled yet (see UnrecognizedLine).

    Genuinely malformed lines are NOT represented here -- those fail the
    whole parse (see typeb.messages.booking.parse_booking_message's
    docstring for the malformed-vs-unrecognized distinction)."""
    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    passengers: list[BookingPassenger]
    name_elements: list[NameElement]
    segments: list[SegmentElement]
    warnings: list[str]
    unrecognized_lines: list[UnrecognizedLine]