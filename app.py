"""
Type B Parser -- Variant B (foundation-first rebuild)

Built alongside the original app.py described in typeb_parser_handoff.md,
for direct comparison. Scope right now: AVN, RVR, and booking-hold
messages -- see typeb/tables/data/message_identifiers.yaml for what's
recognized vs. what's actually implemented (meta.supported).

Run:
    python app.py

Test with Hoppscotch against http://localhost:5000
"""
from flask import Flask, jsonify, request

from typeb.elements.cross_reference import CrossReferenceError
from typeb.elements.errors import ElementParseError
from typeb.envelope.parser import EnvelopeParseError, parse_envelope
from typeb.messages.avn import parse_availability_message
from typeb.messages.booking import parse_booking_message
from typeb.messages.rvr import parse_recap_message
from typeb.tables import loader

from datetime import datetime, timezone
 
from pydantic import ValidationError
 
from typeb.reply.cases.booking_confirm import (
    ReplyGenerationError,
    generate_booking_confirm_reply,
)
from typeb.reply.decision import ReplyDecision
from typeb.reply.envelope import ReplyEnvelopeError
from typeb.reply.rules import ReplyRuleError


app = Flask(__name__)

# Load + validate every reference table at import time, not on first
# request. If a YAML table is malformed, we want the app to refuse to
# start rather than fail confusingly on whichever request touches the
# bad table first.
_TABLES = loader.load_all()

# Dispatch table: envelope.effective_identifier -> orchestrator function.
# Each orchestrator takes raw Type B text and returns a frozen Pydantic
# message model.
_ORCHESTRATORS = {
    "BOOKING": parse_booking_message,
    "AVN": parse_availability_message,
    "RVR": parse_recap_message,
}

def _current_ddhhmm() -> str:
    """REQ03's date/time group has no month/year -- day of month + 24hr
    time only. UTC, since Type B has no timezone field of its own."""
    return datetime.now(timezone.utc).strftime("%d%H%M")



@app.get("/health")
def health():
    """Confirms the app started and every reference table loaded and
    validated cleanly. Try this first in Hoppscotch."""
    return jsonify({
        "status": "ok",
        "tables_loaded": {name: len(table) for name, table in _TABLES.items()},
    })


@app.post("/parse")
def parse_message():
    """Parse a raw Type B message into JSON. Dispatches to the right
    orchestrator based on the message's identifier (or the implicit
    BOOKING type when there's no identifier line).

    Body: raw Type B text (Content-Type: text/plain), not JSON.
    Scope right now: AVN, RVR, and booking-hold messages only.
    """
    raw = request.get_data(as_text=True)
    if not raw or not raw.strip():
        return jsonify({
            "error": "Request body is empty -- expected raw Type B text."
        }), 400

    try:
        envelope, _ = parse_envelope(raw)
    except EnvelopeParseError as e:
        return jsonify({"error": str(e)}), 400

    orchestrator = _ORCHESTRATORS.get(envelope.effective_identifier)
    if orchestrator is None:
        return jsonify({
            "error": (
                f"Message identifier {envelope.effective_identifier!r} is "
                f"recognized but not yet supported by this API. "
                f"Currently supported: {sorted(_ORCHESTRATORS)}."
            )
        }), 400

    try:
        message = orchestrator(raw)
    except (ElementParseError, CrossReferenceError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "data": message.model_dump(),
        "detected_msg_id": envelope.effective_identifier,
    })

@app.post("/reply")
def reply_message():
    """Generate a Type B reply from a Type B request.
 
    Two ways to call this, dispatched by Content-Type:
 
    1. text/plain -- body is just the raw Type B request text. Always
       defaults to ReplyDecision.confirm_all() (every segment -> KK),
       with the reply timestamp set to the current time. Convenient for
       manual/quick testing; no way to specify TK/UC/etc.
 
    2. application/json -- body is
           { "message": "<raw text>", "decision": {...} }
       for full control over the reply outcome and timestamp. Response
       includes reply_parsed -- the generated reply run back through
       parse_booking_message, both as a convenience (callers who want
       the structured view don't need a second request) and as a
       built-in sanity check (a malformed render surfaces as a 500
       instead of shipping broken Type B text silently).
 
    Response:
      text/plain in  -> text/plain out (the raw reply text)
      application/json in -> { "reply": "<raw reply text>",
                                "reply_parsed": {...} }
    """
    content_type = (request.content_type or "").split(";")[0].strip()
 
    if content_type == "application/json":
        body = request.get_json(silent=True)
        if not body or "message" not in body:
            return jsonify({
                "error": "Expected JSON body with a 'message' field "
                         "containing the raw Type B request text."
            }), 400
        raw = body["message"]
        if "decision" not in body:
            return jsonify({
                "error": "Expected a 'decision' field describing the "
                         "reply outcome (see ReplyDecision)."
            }), 400
        try:
            decision = ReplyDecision.model_validate(body["decision"])
        except ValidationError as e:
            return jsonify({"error": f"Malformed 'decision': {e}"}), 400
        respond_as_json = True
    else:
        raw = request.get_data(as_text=True)
        decision = None  # built after parsing, once segment count is known
        respond_as_json = False
 
    if not raw or not raw.strip():
        error = "Request body is empty -- expected raw Type B text."
        return (jsonify({"error": error}), 400) if respond_as_json else (error, 400)
 
    try:
        message = parse_booking_message(raw)
    except (EnvelopeParseError, ElementParseError, CrossReferenceError) as e:
        return (jsonify({"error": str(e)}), 400) if respond_as_json else (str(e), 400)
 
    if decision is None:
        decision = ReplyDecision.confirm_all(
            message.segments, reply_date_time_raw=_current_ddhhmm()
        )
 
    try:
        reply = generate_booking_confirm_reply(message, decision)
    except (ReplyGenerationError, ReplyEnvelopeError, ReplyRuleError) as e:
        return (jsonify({"error": str(e)}), 400) if respond_as_json else (str(e), 400)
 
    if not respond_as_json:
        return reply, 200, {"Content-Type": "text/plain"}
 
    try:
        reply_parsed = parse_booking_message(reply)
    except (EnvelopeParseError, ElementParseError, CrossReferenceError) as e:
        return jsonify({
            "error": f"Generated reply failed to re-parse (internal "
                     f"render bug, please report): {e}",
            "reply": reply,
        }), 500
 
    return jsonify({"reply": reply, "reply_parsed": reply_parsed.model_dump()})



if __name__ == "__main__":
    app.run(debug=True)