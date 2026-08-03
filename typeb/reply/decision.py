from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SegmentDecision(BaseModel):
    """Caller's outcome for one request segment, matched by position
    (segments[i] in the request -> decisions[i] here). REQ03 section 19:
    the KK/TK/UU/UC/TL choice depends on real inventory the parser has
    no way to know, so it's always an explicit input, never derived.

    confirmed_times_raw is required when action_code is "TK" or "TL"
    (REQ03 p.49/62: those two codes exist specifically to carry a
    corrected time), and must be None otherwise -- a KK reply drops
    times entirely per the "no arrival/continuation information" rule.
    """
    model_config = ConfigDict(frozen=True)

    action_code: str
    number_in_party: int
    confirmed_times_raw: tuple[str, str] | None = None


class ReplyDecision(BaseModel):
    """Everything about the reply's OUTCOME that the request alone can't
    supply. own_record_locator is optional and unconfirmed -- flagged as
    an open question pending Parka's answer on whether a responder ever
    needs to add its own record locator line beyond echoing the
    request's."""
    model_config = ConfigDict(frozen=True)

    reply_date_time_raw: str
    segment_decisions: list[SegmentDecision]
    own_record_locator: str | None = None

    @classmethod
    def confirm_all(
        cls, segments: list, reply_date_time_raw: str
    ) -> "ReplyDecision":
        """Default-everything-to-KK helper for the current stage of
        development -- richer decision input (real inventory checks,
        TK/UU/UC outcomes) comes later."""
        return cls(
            reply_date_time_raw=reply_date_time_raw,
            segment_decisions=[
                SegmentDecision(action_code="KK", number_in_party=s.number_in_party)
                for s in segments
            ],
        )