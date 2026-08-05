from __future__ import annotations

from typeb.elements.cross_reference import cross_reference_passengers, validate_party_size
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_line
from typeb.elements.osi import parse_osi_line
from typeb.elements.segment import parse_segment_element
from typeb.elements.ssr import parse_ssr_line
from typeb.elements.tokenizer import ElementKind, tokenize_body
from typeb.envelope.parser import parse_envelope
from typeb.model.booking import BookingMessage
from typeb.model.common import UnrecognizedLine
from typeb.model.elements import (
    NameElement,
    OsiRecordLocatorElement,
    SegmentElement,
    SsrRecordLocatorElement,
)


def parse_booking_message(raw: str) -> BookingMessage:
    envelope, body_lines = parse_envelope(raw)

    if envelope.effective_identifier != "BOOKING":
        raise ElementParseError(
            f"parse_booking_message called on a non-booking message "
            f"(identifier={envelope.effective_identifier!r})."
        )

    name_elements: list[NameElement] = []
    segments: list[SegmentElement] = []
    contact_elements: list = []
    unrecognized: list[UnrecognizedLine] = []

    for kind, line in tokenize_body(body_lines):
        try:
            if kind == ElementKind.NAME:
                name_elements.extend(parse_name_line(line))
            elif kind == ElementKind.SEGMENT:
                segments.append(parse_segment_element(line))
            elif kind == ElementKind.SSR:
                contact_elements.append(parse_ssr_line(line))
            elif kind == ElementKind.OSI:
                contact_elements.append(parse_osi_line(line))
            elif kind == ElementKind.MARKER:
                continue
            elif kind in (ElementKind.AVAILABILITY_LINE, ElementKind.RECAP_LINE):
                raise ElementParseError(
                    f"Unexpected {kind.value} shape inside a booking "
                    f"message body: {line!r}"
                )
            else:
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

    airline_record_locators = [
        e.record_locator
        for e in contact_elements
        if isinstance(e, (SsrRecordLocatorElement, OsiRecordLocatorElement))
    ]

    warnings: list[str] = []
    for segment in segments:
        warnings.extend(validate_party_size(name_elements, segment.number_in_party))

    return BookingMessage(
        envelope=envelope,
        passengers=passengers,
        name_elements=name_elements,
        segments=segments,
        airline_record_locators=airline_record_locators,
        warnings=warnings,
        unrecognized_lines=unrecognized,
    )