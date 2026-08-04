"""
Body tokenizer: classifies each body line (as returned by
parse_envelope()) into an element kind by shape, before dispatching to
the matching element parser. 
"""
from __future__ import annotations

import re
from enum import Enum

# REQ03 p.9-10: number-in-party digits (1-3) glued to a surname of at
# least 2 letters. See module docstring for why 2+ letters specifically.
_NAME_LINE_RE = re.compile(r"^\d{1,3}[A-Z]{2,}")

# REQ03 p.9-10 booking SEGMENT first token: airline(2, alnum) + flight
# number (2-4 digits) + RBD (1 letter) + date (2-digit day + 3-letter
# month), all glued, e.g. "8G083F24SEP".
_SEGMENT_FIRST_TOKEN_RE = re.compile(r"^[A-Z0-9]{2}\d{2,4}[A-Z]\d{2}[A-Z]{3}$")

# REQ02 p.7-8 AVN first token: airline(2, alnum) + flight number
# (1-4 digits, optional trailing letter suffix), SPACED from the rest,
# e.g. "AA800".
_AVAIL_FIRST_TOKEN_RE = re.compile(r"^[A-Z0-9]{2}\d{1,4}[A-Z]?$")

# REQ02 p.13-14 RVR request line: airline(2, alnum) + flight number
# (1-4 digits, optional trailing letter) immediately followed by '/'.
# Matches BOTH documented shapes -- date-range ("8G407/16JUN26-
# 30DEC26/1234567", 2 slashes, no spaces) and single-date
# ("8G123/16JUN26 CGKSIN", 1 slash, optional space + route)
_RECAP_LINE_START_RE = re.compile(r"^[A-Z0-9]{2}\d{1,4}[A-Z]?/")

_MARKERS = {"NNNN", "ARNK", "//"}


class ElementKind(str, Enum):
    NAME = "NAME"
    SEGMENT = "SEGMENT"
    AVAILABILITY_LINE = "AVAILABILITY_LINE"
    RECAP_LINE = "RECAP_LINE"
    SSR = "SSR"
    OSI = "OSI"
    MARKER = "MARKER"
    UNKNOWN = "UNKNOWN"


def classify_line(line: str) -> ElementKind:
    stripped = line.strip()

    if stripped in _MARKERS:
        return ElementKind.MARKER

    if stripped.startswith("SSR "):
        return ElementKind.SSR

    if stripped.startswith("OSI "):
        return ElementKind.OSI

    if _NAME_LINE_RE.match(stripped):
        return ElementKind.NAME

    tokens = stripped.split()

    if tokens and _SEGMENT_FIRST_TOKEN_RE.match(tokens[0]) and len(tokens) >= 3:
        return ElementKind.SEGMENT

    if _RECAP_LINE_START_RE.match(stripped):
        return ElementKind.RECAP_LINE

    if len(tokens) == 4 and _AVAIL_FIRST_TOKEN_RE.match(tokens[0]):
        return ElementKind.AVAILABILITY_LINE

    return ElementKind.UNKNOWN


def tokenize_body(body_lines: list[str]) -> list[tuple[ElementKind, str]]:
    return [(classify_line(line), line) for line in body_lines]