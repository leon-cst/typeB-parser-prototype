from __future__ import annotations

from typeb.elements.cross_reference import cross_reference_passengers, validate_party_size
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_line
from typeb.elements.osi import parse_osi_line
from typeb.elements.segment import parse_segment_element
from typeb.elements.ssr import parse_ssr_line
from typeb.elements.tokenizer import ElementKind, tokenize_body
from typeb.envelope.parser import _DEFAULT_MAX_LINE_LENGTH, parse_envelope
from typeb.model.common import UnrecognizedLine
from typeb.model.dvd import DvdMessage
from typeb.model.elements import NameElement, OsiOriginalLocatorElement, SegmentElement


def parse_dvd_message(raw: str) -> DvdMessage:
    envelope, body_lines, warnings = parse_envelope(raw)

    if envelope.effective_identifier != "DVD":
        raise ElementParseError(
            f"parse_dvd_message called on a non-DVD message "
            f"(identifier={envelope.effective_identifier!r})."
        )

    name_elements: list[NameElement] = []
    segments: list[SegmentElement] = []
    contact_elements: list = []
    unrecognized: list[UnrecognizedLine] = []

    for kind, line in tokenize_body(body_lines):
        if len(line) > _DEFAULT_MAX_LINE_LENGTH:
            # excluded rather than parsed, with a warning -- see
            # typeb.messages.booking for the same behavior + rationale
            warnings.append(
                f"Line excluded from parsing, {len(line)} characters "
                f"exceeding the {_DEFAULT_MAX_LINE_LENGTH}-character "
                f"limit (REQ03 section 3): {line!r}"
            )
            unrecognized.append(
                UnrecognizedLine(
                    raw=line,
                    tokenizer_kind=kind.value,
                    reason=f"Line exceeds {_DEFAULT_MAX_LINE_LENGTH}-character limit",
                )
            )
            continue

        try:
            if kind == ElementKind.NAME:
                name_elements.extend(parse_name_line(line))
            elif kind == ElementKind.SEGMENT:
                try:
                    segments.append(parse_segment_element(line))
                except ElementParseError as e:
                    # REQ03 section 24's own worked example has a
                    # malformed segment line (no action code) -- degrade
                    # to unrecognized rather than fail the whole message
                    unrecognized.append(
                        UnrecognizedLine(raw=line, tokenizer_kind=kind.value, reason=str(e))
                    )
            elif kind == ElementKind.SSR:
                contact_elements.append(parse_ssr_line(line))
            elif kind == ElementKind.OSI:
                contact_elements.append(parse_osi_line(line))
            elif kind == ElementKind.MARKER:
                continue
            elif kind == ElementKind.CHNT:
                # not observed in any DVD worked example (REQ03 section
                # 24) -- refuse rather than silently reinterpret
                raise ElementParseError(
                    f"CHNT is not a documented part of DVD messages "
                    f"(REQ03 section 24): {line!r}"
                )
            elif kind in (ElementKind.AVAILABILITY_LINE, ElementKind.RECAP_LINE):
                raise ElementParseError(
                    f"Unexpected {kind.value} shape inside a DVD "
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

    original_locators = [
        e for e in contact_elements if isinstance(e, OsiOriginalLocatorElement)
    ]

    for segment in segments:
        for warning in validate_party_size(name_elements, segment.number_in_party):
            if warning not in warnings:
                warnings.append(warning)

    return DvdMessage(
        envelope=envelope,
        passengers=passengers,
        name_elements=name_elements,
        segments=segments,
        original_locators=original_locators,
        warnings=warnings,
        unrecognized_lines=unrecognized,
    )