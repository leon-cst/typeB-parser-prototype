"""Shared models used across multiple message-type orchestrators
(typeb.messages.booking, .avn, .rvr, and future ones)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UnrecognizedLine(BaseModel):
    """A body line that is structurally fine but has no implemented
    parser yet (e.g. an SSR code beyond FOID/INFT/CHLD), or that matched
    no known element shape at all. Collected rather than treated as a
    parse failure -- see UnrecognizedElementError's docstring for the
    policy this implements: a real message containing one out-of-scope
    line shouldn't block parsing everything else in it."""
    model_config = ConfigDict(frozen=True)

    raw: str
    tokenizer_kind: str  # the ElementKind the tokenizer assigned, e.g. "SSR", "UNKNOWN"
    reason: str