from __future__ import annotations

from typeb.model.booking import BookingMessage
from typeb.reply.decision import ReplyDecision
from typeb.reply.envelope import build_reply_envelope
from typeb.reply.render import render_reply
from typeb.reply.rules import ReplyRuleError, apply_segment_decision


class ReplyGenerationError(Exception):
    pass


def generate_booking_confirm_reply(
    message: BookingMessage, decision: ReplyDecision
) -> str:
    """REQ03 section 19 basic reply, p.49 worked example: record
    locator + name + segment elements only, times dropped unless the
    segment's advice code is TK/TL."""
    if len(decision.segment_decisions) != len(message.segments):
        raise ReplyGenerationError(
            f"Expected one decision per request segment, got "
            f"{len(decision.segment_decisions)} for "
            f"{len(message.segments)} segments"
        )

    reply_envelope = build_reply_envelope(
        message.envelope, decision.reply_date_time_raw
    )

    try:
        reply_segments = [
            apply_segment_decision(segment, seg_decision)
            for segment, seg_decision in zip(message.segments, decision.segment_decisions)
        ]
    except ReplyRuleError as e:
        raise ReplyGenerationError(str(e)) from e

    return render_reply(
        envelope=reply_envelope,
        name_elements=message.name_elements,
        segments=reply_segments,
    )