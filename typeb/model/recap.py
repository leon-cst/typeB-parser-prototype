"""Output model for a fully parsed RVR (availability recap request)
message -- see typeb.messages.rvr for the function that builds these."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import RecapDateRangeLine, RecapSingleDateLine
from typeb.model.envelope import Envelope


class RecapMessage(BaseModel):
    """RVR body has no passengers or cross-referencing -- just a flat
    list of recap lines, one per requested flight. Each line is one of
    two documented shapes (RecapDateRangeLine or RecapSingleDateLine) --
    see typeb.elements.recap's module docstring for the distinction."""
    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    recap_lines: list[RecapDateRangeLine | RecapSingleDateLine]
    unrecognized_lines: list[UnrecognizedLine]