from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SegmentDecision(BaseModel):
    """Caller's outcome for one request segment, matched by position
    (segments[i] in the request -> decisions[i] here).
    """
    model_config = ConfigDict(frozen=True)

    action_code: str
    number_in_party: int
    confirmed_times_raw: tuple[str, str] | None = None


class ReplyDecision(BaseModel):
    """Everything about the reply's OUTCOME that the request alone can't
    supply. own_record_locator is optional and unconfirmed (open to change)"""
    model_config = ConfigDict(frozen=True)

    reply_date_time_raw: str
    segment_decisions: list[SegmentDecision]
    own_record_locator: str | None = None

    @classmethod
    def confirm_all(
        cls, segments: list, reply_date_time_raw: str
    ) -> "ReplyDecision":
        """Default-everything-to-KK helper for the current stage of
        development (More decision input like real inventory checks,
        TK/UU/UC outcomes will come later)."""
        return cls(
            reply_date_time_raw=reply_date_time_raw,
            segment_decisions=[
                SegmentDecision(action_code="KK", number_in_party=s.number_in_party)
                for s in segments
            ],
        )