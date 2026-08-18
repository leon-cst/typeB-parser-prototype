"""Domain model for DVD (Divide PNR) messages, REQ03 section 24."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import NameElement, OsiOriginalLocatorElement, SegmentElement
from typeb.model.envelope import Envelope
from typeb.model.passenger import BookingPassenger


class DvdMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    passengers: list[BookingPassenger]
    name_elements: list[NameElement]
    segments: list[SegmentElement]
    # REQ03 section 24: every DVD message must carry the original PNR
    # this divide refers back to -- required content, not optional.
    original_locators: list[OsiOriginalLocatorElement]
    warnings: list[str]
    unrecognized_lines: list[UnrecognizedLine]