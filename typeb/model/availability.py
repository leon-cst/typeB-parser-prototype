"""Output model for a fully parsed AVN (availability numeric) message --
see typeb.messages.avn for the function that builds these."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import AvailabilityLine
from typeb.model.envelope import Envelope


class AvailabilityMessage(BaseModel):
    """AVN body has no passengers or cross-referencing -- just a flat
    list of AvailabilityLine, one per requested flight/class/date."""
    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    availability_lines: list[AvailabilityLine]
    unrecognized_lines: list[UnrecognizedLine]