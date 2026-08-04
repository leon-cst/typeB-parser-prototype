"""Output model for a fully parsed RVR (availability recap request)
message -- see typeb.messages.rvr for the function that builds these."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from typeb.model.common import UnrecognizedLine
from typeb.model.elements import RecapDateRangeLine, RecapSingleDateLine
from typeb.model.envelope import Envelope


class RecapMessage(BaseModel):

    model_config = ConfigDict(frozen=True)

    envelope: Envelope
    recap_lines: list[RecapDateRangeLine | RecapSingleDateLine]
    unrecognized_lines: list[UnrecognizedLine]