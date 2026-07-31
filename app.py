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


if __name__ == "__main__":
    app.run(debug=True)