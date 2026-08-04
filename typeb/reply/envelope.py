from __future__ import annotations

from typeb.model.envelope import CommReference, Envelope


class ReplyEnvelopeError(Exception):
    pass


def build_reply_envelope(
    request: Envelope, reply_date_time_raw: str
) -> Envelope:
    """Swap destination address <-> comm-ref origin (REQ03 p.49 request/
    response pair). Record locators are echoed unchanged. See
    typeb.reply.decision.ReplyDecision for the open question of when a
    responder needs to add its own.

    Raises if the request has more than one address"""
    if len(request.addresses) != 1:
        raise ReplyEnvelopeError(
            f"Reply envelope generation only supports single-address "
            f"requests for now, got {len(request.addresses)}"
        )

    return Envelope(
        priority_code=request.priority_code,
        addresses=[request.comm_reference.origin],
        comm_reference=CommReference(
            origin=request.addresses[0],
            date_time_raw=reply_date_time_raw,
        ),
        message_identifier=request.message_identifier,
        record_locators=request.record_locators,
    )