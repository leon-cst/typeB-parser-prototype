"""
Booking message orchestrator: raw Type B text in, one BookingMessage out.

Malformed vs. unrecognized:
    - Malformed is structurally wrong
    - Unrecognized is structurally correct but the program fails to identify the line type
    - Malformed lines will fail to parse, unrecognized lines are indicated in its own reply section

"""
from __future__ import annotations

from typeb.elements.cross_reference import cross_reference_passengers, validate_party_size
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_element
from typeb.elements.osi import parse_osi_line
from typeb.elements.segment import parse_segment_element
from typeb.elements.ssr import parse_ssr_line
from typeb.elements.tokenizer import ElementKind, tokenize_body
from typeb.envelope.parser import parse_envelope
from typeb.model.booking import BookingMessage, UnrecognizedLine
from typeb.model.elements import NameElement, SegmentElement


def parse_booking_message(raw: str) -> BookingMessage:
    envelope, body_lines = parse_envelope(raw)  # hard fails on its own if malformed

    if envelope.effective_identifier != "BOOKING":
        raise ElementParseError(
            f"parse_booking_message called on a non-booking message "
            f"(identifier={envelope.effective_identifier!r}) -- this "
            f"orchestrator is booking-specific; AVN/RVR have their own "
            f"body grammar entirely."
        )

    name_elements: list[NameElement] = []
    segments: list[SegmentElement] = []
    contact_elements: list = []  # SSR/OSI results, each carries a .name
    unrecognized: list[UnrecognizedLine] = []

    for kind, line in tokenize_body(body_lines):
        try:
            if kind == ElementKind.NAME:
                name_elements.append(parse_name_element(line))
            elif kind == ElementKind.SEGMENT:
                segments.append(parse_segment_element(line))
            elif kind == ElementKind.SSR:
                contact_elements.append(parse_ssr_line(line))
            elif kind == ElementKind.OSI:
                contact_elements.append(parse_osi_line(line))
            elif kind == ElementKind.MARKER:
                continue  # NNNN / ARNK / '//' -- structural, not data-bearing
            elif kind in (ElementKind.AVAILABILITY_LINE, ElementKind.RECAP_LINE):

                raise ElementParseError(
                    f"Unexpected {kind.value} shape inside a booking "
                    f"message body: {line!r}"
                )
            else:  # ElementKind.UNKNOWN
                unrecognized.append(
                    UnrecognizedLine(
                        raw=line,
                        tokenizer_kind=kind.value,
                        reason="Line did not match any known element shape",
                    )
                )
        except UnrecognizedElementError as e:
            unrecognized.append(
                UnrecognizedLine(raw=line, tokenizer_kind=kind.value, reason=str(e))
            )


    passengers = cross_reference_passengers(name_elements, contact_elements)

    warnings: list[str] = []
    for segment in segments:
        warnings.extend(validate_party_size(name_elements, segment.number_in_party))

    return BookingMessage(
        envelope=envelope,
        passengers=passengers,
        name_elements=name_elements,
        segments=segments,
        warnings=warnings,
        unrecognized_lines=unrecognized,
    )