"""
Body tokenizer: classifies each body line (as returned by
parse_envelope()) into an element kind by shape, before dispatching to
the matching element parser. Purely shape-based, like the envelope
parser -- no message-type context needed, because the shapes in current
scope (AVN, RVR, booking) don't overlap.

A subtlety worth documenting because it caused a real bug during
development: the NAME-line rule (REQ03 p.9-10) is "1-3 digits glued
directly to text". A naive regex for that -- digit(s) followed by ANY
non-space character -- also matches booking SEGMENT lines whose airline
code starts with a digit, which is common (8G, 5J, 3U, 9C, ...): the
line "8G083F24SEP CGKDPS NN1 0910 1015" starts with "8" then "G", which
satisfies "digit followed by a non-space character" just as much as
"1RAHARJO/..." does.

The fix: require 2+ CONSECUTIVE letters immediately after the leading
digits, not just one. This works because Type B airline codes are always
exactly 2 characters (REQ03 section 2) -- so a digit-led airline code has
at most ONE letter before flight-number digits resume ("8" + "G" + "083..."),
while a real surname is realistically always 2+ letters ("RAHARJO",
"BORGE", ...). See test_tokenizer.py for the regression case.
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
# ("8G123/16JUN26 CGKSIN", 1 slash, optional space + route) -- since
# what distinguishes a recap line from everything else is this specific
# start shape, not slash count or space presence (which differ between
# the two sub-shapes themselves).
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
    """Classify every body line. Returns (kind, raw_line) pairs in order.
    A line this can't confidently classify comes back as UNKNOWN rather
    than raising -- classification failure on one line shouldn't block
    classifying the rest of the message; the caller decides what to do
    with UNKNOWN lines (raise, log, or route to a dead-letter path)."""
    return [(classify_line(line), line) for line in body_lines]