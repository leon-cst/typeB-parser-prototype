"""Shared models used across multiple message-type orchestrators
(typeb.messages.booking, .avn, .rvr, and future ones)."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class UnrecognizedLine(BaseModel):

    model_config = ConfigDict(frozen=True)

    raw: str
    tokenizer_kind: str  # the ElementKind the tokenizer assigned, e.g. "SSR", "UNKNOWN"
    reason: str