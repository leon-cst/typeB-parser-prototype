from __future__ import annotations
from pydantic import BaseModel, ConfigDict, computed_field

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import (
    AutomatedSsrElement,
    NameElement,
    OsiContactAddressElement,
    OsiPartyCountElement,
    SegmentElement,
    SsrGroupFareElement,
    SsrGroupSeatElement,
)
from typeb.model.envelope import Envelope
from typeb.model.passenger import BookingPassenger


class GroupPlaceholder(BaseModel):

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
    replacement_name_elements: list[NameElement] = []
    group_placeholders: list[GroupPlaceholder]
    arrival_elements: list[SegmentElement]
    segments: list[SegmentElement]
    airline_record_locators: list[str]
    group_fare_info: list[SsrGroupFareElement]
    group_seat_requests: list[SsrGroupSeatElement]
    contact_addresses: list[OsiContactAddressElement]
    party_count_notices: list[OsiPartyCountElement] = []
    automated_ssrs: list[AutomatedSsrElement] = []
    warnings: list[str]
    unrecognized_lines: list[UnrecognizedLine]

    @computed_field
    @property
    def is_name_change(self) -> bool:
        return bool(self.replacement_name_elements)