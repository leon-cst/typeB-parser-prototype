from __future__ import annotations
import re
from enum import Enum

_NAME_LINE_RE = re.compile(r"^\d{1,3}[A-Z]{2,}")
_SEGMENT_FIRST_TOKEN_RE = re.compile(r"^[A-Z0-9]{2}\d{2,4}[A-Z]\d{2}[A-Z]{3}$")
_AVAIL_FIRST_TOKEN_RE = re.compile(r"^[A-Z0-9]{2}\d{1,4}[A-Z]?$")
_RECAP_LINE_START_RE = re.compile(r"^[A-Z0-9]{2}\d{1,4}[A-Z]?/")
_MARKERS = {"NNNN", "ARNK", "//"}
_CHNT = "CHNT"
_SEGMENT_FIRST_TOKEN_NO_DATE_RE = re.compile(r"^[A-Z0-9]{2}\d{2,4}[A-Z]$")
_BARE_DATE_RE = re.compile(r"^\d{2}[A-Z]{3}$")


def _reglue_split_date(line: str) -> str:

    tokens = line.strip().split()
    if (
        len(tokens) >= 2
        and _SEGMENT_FIRST_TOKEN_NO_DATE_RE.match(tokens[0])
        and _BARE_DATE_RE.match(tokens[1])
    ):
        return " ".join([tokens[0] + tokens[1]] + tokens[2:])
    return line


class ElementKind(str, Enum):
    NAME = "NAME"
    SEGMENT = "SEGMENT"
    AVAILABILITY_LINE = "AVAILABILITY_LINE"
    RECAP_LINE = "RECAP_LINE"
    SSR = "SSR"
    OSI = "OSI"
    MARKER = "MARKER"
    CHNT = "CHNT"
    UNKNOWN = "UNKNOWN"


def classify_line(line: str) -> ElementKind:
    stripped = _reglue_split_date(line.strip())
    if stripped in _MARKERS:
        return ElementKind.MARKER

    if stripped == _CHNT:
        return ElementKind.CHNT
    
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
    return [
        (classify_line(line), _reglue_split_date(line.strip()))
        for line in body_lines
    ]