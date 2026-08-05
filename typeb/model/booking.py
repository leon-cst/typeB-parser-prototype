from __future__ import annotations
from pydantic import BaseModel, ConfigDict

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import NameElement, SegmentElement
from typeb.model.envelope import Envelope
from typeb.model.passenger import BookingPassenger


class BookingMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    passengers: list[BookingPassenger]
    name_elements: list[NameElement]
    segments: list[SegmentElement]
    airline_record_locators: list[str]
    warnings: list[str]
    unrecognized_lines: list[UnrecognizedLine]