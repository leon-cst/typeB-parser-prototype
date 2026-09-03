"""Domain model for DVD (Divide PNR) messages, REQ03 section 24."""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict, computed_field

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import (
    AutomatedSsrElement,
    NameChange,
    NameElement,
    OsiOriginalLocatorElement,
    OsiPartyCountElement,
    SegmentElement,
)
from typeb.model.envelope import Envelope
from typeb.model.passenger import BookingPassenger


class DvdMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    airline_record_locators: list[str]
    party_count_notices: list[OsiPartyCountElement] = []
    automated_ssrs: list[AutomatedSsrElement] = []
    passengers: list[BookingPassenger]
    name_elements: list[NameElement]
    name_changes: list[NameChange] = []
    segments: list[SegmentElement]
    original_locators: list[OsiOriginalLocatorElement]
    record_locator_recovered_from_osi: bool = False
    warnings: list[str]
    unrecognized_lines: list[UnrecognizedLine]

    @computed_field
    @property
    def is_name_change(self) -> bool:
        return bool(self.name_changes)