"""Shared body-tokenization logic for message types built on the same
NAME/CHNT/SEGMENT/SSR/OSI grammar (currently: booking, DVD). Not a
message type of its own, just the common middle of each orchestrator,
factored out so a fix to one (e.g. line-length exclusion, CHNT
handling) doesn't have to be duplicated in the other.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import (
    EXCLUDED_NAME_LINE_MARKER,
    NameChange,
    apply_name_changes,
    parse_name_line,
    split_name_change_boundary,
)
from typeb.elements.osi import parse_osi_line
from typeb.elements.segment import parse_segment_element
from typeb.elements.ssr import parse_ssr_line
from typeb.elements.tokenizer import ElementKind, tokenize_body
from typeb.envelope.parser import _DEFAULT_MAX_LINE_LENGTH
from typeb.model.common import UnrecognizedLine
from typeb.model.elements import NameElement, SegmentElement


@dataclass
class ParsedBody:
    name_elements: list[NameElement]  # full pre-CHNT passenger list
    name_changes: list[NameChange]
    current_name_elements: list[NameElement]  # post-CHNT (apply_name_changes)
    segments: list[SegmentElement]
    contact_elements: list = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unrecognized_lines: list[UnrecognizedLine] = field(default_factory=list)


def parse_shared_body(
    body_lines: list[str],
    warnings: list[str],
    *,
    allow_malformed_segments: bool = False,
) -> ParsedBody:
    name_lines: list[str] = []
    segments: list[SegmentElement] = []
    contact_elements: list = []
    unrecognized: list[UnrecognizedLine] = []

    for kind, line in tokenize_body(body_lines):
        if len(line) > _DEFAULT_MAX_LINE_LENGTH:
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
            if kind == ElementKind.NAME:
                # Sentinel so split_name_change_boundary can tell "a
                # NAME line was here but excluded" apart from "there
                # was no NAME line here at all".
                name_lines.append(EXCLUDED_NAME_LINE_MARKER)
            continue

        try:
            if kind in (ElementKind.NAME, ElementKind.CHNT):
                name_lines.append(line)
            elif kind == ElementKind.SEGMENT:
                if allow_malformed_segments:
                    try:
                        segments.append(parse_segment_element(line))
                    except ElementParseError as e:
                        unrecognized.append(
                            UnrecognizedLine(raw=line, tokenizer_kind=kind.value, reason=str(e))
                        )
                else:
                    segments.append(parse_segment_element(line))
            elif kind == ElementKind.SSR:
                contact_elements.append(parse_ssr_line(line))
            elif kind == ElementKind.OSI:
                contact_elements.append(parse_osi_line(line))
            elif kind == ElementKind.MARKER:
                continue
            elif kind in (ElementKind.AVAILABILITY_LINE, ElementKind.RECAP_LINE):
                raise ElementParseError(
                    f"Unexpected {kind.value} shape inside a message body: {line!r}"
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

    name_elements, name_changes = split_name_change_boundary(name_lines)
    current_name_elements = apply_name_changes(name_elements, name_changes)

    return ParsedBody(
        name_elements=name_elements,
        name_changes=name_changes,
        current_name_elements=current_name_elements,
        segments=segments,
        contact_elements=contact_elements,
        warnings=warnings,
        unrecognized_lines=unrecognized,
    )