from __future__ import annotations

from typeb.model.elements import SegmentElement
from typeb.reply.decision import SegmentDecision


class ReplyRuleError(Exception):
    pass


def apply_segment_decision(
    segment: SegmentElement, decision: SegmentDecision
) -> SegmentElement:
    """REQ03 section 19: reply segments drop the request's times ("do
    not include reply message any arrival and/or continuation
    information") unless the advice code is TK or TL, in which case the
    corrected time must be included (REQ03 p.49, p.62 worked examples)."""
    needs_times = decision.action_code in ("TK", "TL")

    if needs_times and decision.confirmed_times_raw is None:
        raise ReplyRuleError(
            f"Action code {decision.action_code!r} requires "
            f"confirmed_times_raw (REQ03 p.49/62)"
        )
    if not needs_times and decision.confirmed_times_raw is not None:
        raise ReplyRuleError(
            f"Action code {decision.action_code!r} must not carry "
            f"times -- only TK/TL do (REQ03 section 19)"
        )

    departure_time_raw, arrival_time_raw = (
        decision.confirmed_times_raw if needs_times else (None, None)
    )

    return segment.model_copy(
        update={
            "action_code": decision.action_code,
            "number_in_party": decision.number_in_party,
            "departure_time_raw": departure_time_raw,
            "arrival_time_raw": arrival_time_raw,
        }
    )