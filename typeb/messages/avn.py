"""
AVN (availability numeric) message orchestrator: raw Type B text in, one
AvailabilityMessage out.

"""
from __future__ import annotations

from typeb.elements.availability import parse_availability_line
from typeb.elements.errors import ElementParseError
from typeb.elements.tokenizer import ElementKind, tokenize_body
from typeb.envelope.parser import parse_envelope
from typeb.model.availability import AvailabilityMessage
from typeb.model.common import UnrecognizedLine

_WRONG_FAMILY_KINDS = {
    ElementKind.NAME,
    ElementKind.SEGMENT,
    ElementKind.SSR,
    ElementKind.OSI,
    ElementKind.RECAP_LINE,
}


def parse_availability_message(raw: str) -> AvailabilityMessage:
    envelope, body_lines = parse_envelope(raw)

    if envelope.effective_identifier != "AVN":
        raise ElementParseError(
            f"parse_availability_message called on a non-AVN message "
            f"(identifier={envelope.effective_identifier!r})."
        )

    availability_lines = []
    unrecognized: list[UnrecognizedLine] = []

    for kind, line in tokenize_body(body_lines):
        if kind == ElementKind.AVAILABILITY_LINE:
            availability_lines.append(parse_availability_line(line))
        elif kind == ElementKind.MARKER:
            continue
        elif kind in _WRONG_FAMILY_KINDS:
            raise ElementParseError(
                f"Unexpected {kind.value} shape inside an AVN message "
                f"body -- every worked AVN example has only availability "
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

    return AvailabilityMessage(
        envelope=envelope,
        availability_lines=availability_lines,
        unrecognized_lines=unrecognized,
    )