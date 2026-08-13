"""
RVR (availability recap request) message orchestrator: raw Type B text
in, one RecapMessage out.

Same malformed-vs-unrecognized policy as booking/AVN
"""
from __future__ import annotations

from typeb.elements.errors import ElementParseError
from typeb.elements.recap import parse_recap_line
from typeb.elements.tokenizer import ElementKind, tokenize_body
from typeb.envelope.parser import parse_envelope
from typeb.model.common import UnrecognizedLine
from typeb.model.recap import RecapMessage

_WRONG_FAMILY_KINDS = {
    ElementKind.NAME,
    ElementKind.SEGMENT,
    ElementKind.SSR,
    ElementKind.OSI,
    ElementKind.AVAILABILITY_LINE,
}


def parse_recap_message(raw: str) -> RecapMessage:
    # RecapMessage has no warnings field yet
    envelope, body_lines, _envelope_warnings = parse_envelope(raw)

    if envelope.effective_identifier != "RVR":
        raise ElementParseError(
            f"parse_recap_message called on a non-RVR message "
            f"(identifier={envelope.effective_identifier!r})."
        )

    recap_lines = []
    unrecognized: list[UnrecognizedLine] = []

    for kind, line in tokenize_body(body_lines):
        if kind == ElementKind.RECAP_LINE:
            recap_lines.append(parse_recap_line(line))
        elif kind == ElementKind.MARKER:
            continue
        elif kind in _WRONG_FAMILY_KINDS:
            raise ElementParseError(
                f"Unexpected {kind.value} shape inside an RVR message "
                f"body -- every worked RVR example has only recap "
                f"lines: {line!r}"
            )
        else:  # ElementKind.UNKNOWN
            unrecognized.append(
                UnrecognizedLine(
                    raw=line,
                    tokenizer_kind=kind.value,
                    reason="Line did not match any known element shape",
                )
            )

    return RecapMessage(
        envelope=envelope,
        recap_lines=recap_lines,
        unrecognized_lines=unrecognized,
    )