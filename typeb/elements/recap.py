"""
RVR recap request line parser.

Two shapes documented in REQ02 pages 12-14 (RVR has no worked examples
in REQ03 at all -- only a one-line mention in the identifier table on
p.8; the earlier attribution to "REQ03 p.13" in this codebase was wrong
and has been corrected):

  Date-range shape (p.13): '<airline><flight>/<start>-<end>/<frequency>'
    e.g. "8G407/16JUN26-30DEC26/1234567" -- 2 '/' characters, no spaces.

  Single-date shape (p.14, two concrete worked examples in one message):
    '<airline><flight>/<date> [<citypair>]'
    e.g. "8G123/16JUN26 CGKSIN" -- 1 '/' character, optional space +
    route. Route may be omitted entirely (REQ02 p.13: "Route tidak
    perlu di isi (berarti all)") -- represented as the literal string
    "ALL", not an error.

Dispatched by '/' count: 2 slashes -> date-range shape, 1 slash ->
single-date shape. This is a reliable structural signal because the
two shapes never overlap in the worked examples -- the date-range shape
has no spaces at all, while the single-date shape's date and route are
space-separated. Anything else raises rather than guessing.

A third, more ambiguous case exists in the doc (p.13's "BPTOPT"
placeholder example, hinting at a possible date-only-no-route form with
some other/no separator) but the only "example" of it uses schematic
placeholder text, not a concrete transmitted line -- not built here;
see typeb.model.elements.RecapSingleDateLine's docstring.
"""
from __future__ import annotations

import re

from typeb.elements.errors import ElementParseError
from typeb.model.elements import RecapDateRangeLine, RecapSingleDateLine

_FIRST_TOKEN_RE = re.compile(r"^(?P<airline>[A-Z0-9]{2})(?P<flight>\d{1,4}[A-Z]?)$")
_DATE_RANGE_RE = re.compile(r"^\d{2}[A-Z]{3}\d{2}-\d{2}[A-Z]{3}\d{2}$")
_SINGLE_DATE_RE = re.compile(r"^\d{2}[A-Z]{3}\d{2}$")


def parse_recap_line(line: str) -> RecapDateRangeLine | RecapSingleDateLine:
    stripped = line.strip()
    slash_count = stripped.count("/")

    if slash_count == 2:
        return _parse_date_range_line(stripped)
    if slash_count == 1:
        return _parse_single_date_line(stripped)

    raise ElementParseError(
        f"Recap request line has {slash_count} '/' characters, expected "
        f"1 (single-date shape) or 2 (date-range shape): {line!r}"
    )


def _parse_date_range_line(stripped: str) -> RecapDateRangeLine:
    parts = stripped.split("/")
    if len(parts) != 3:
        raise ElementParseError(
            f"Date-range recap line should have exactly 3 '/'-separated "
            f"fields: {stripped!r}"
        )
    airline_flight, date_range_raw, frequency_raw = parts

    m = _FIRST_TOKEN_RE.match(airline_flight)
    if not m:
        raise ElementParseError(
            f"Recap line's airline+flight field malformed: "
            f"{airline_flight!r} in {stripped!r}"
        )

    if not _DATE_RANGE_RE.match(date_range_raw):
        raise ElementParseError(
            f"Recap line's date range should be 'ddMMMyy-ddMMMyy' (e.g. "
            f"'16JUN26-30DEC26'): {date_range_raw!r} in {stripped!r}"
        )

    if not frequency_raw:
        raise ElementParseError(f"Recap line's frequency field is empty: {stripped!r}")

    return RecapDateRangeLine(
        raw=stripped,
        airline_code=m.group("airline"),
        flight_number=m.group("flight"),
        date_range_raw=date_range_raw,
        frequency_raw=frequency_raw,
    )


def _parse_single_date_line(stripped: str) -> RecapSingleDateLine:
    airline_flight, _, rest = stripped.partition("/")

    m = _FIRST_TOKEN_RE.match(airline_flight)
    if not m:
        raise ElementParseError(
            f"Recap line's airline+flight field malformed: "
            f"{airline_flight!r} in {stripped!r}"
        )

    tokens = rest.split()
    if len(tokens) == 1:
        date_raw, route = tokens[0], "ALL"
    elif len(tokens) == 2:
        date_raw, route = tokens
    else:
        raise ElementParseError(
            f"Single-date recap line expected '<date>' or "
            f"'<date> <citypair>' after the '/', got {len(tokens)} "
            f"tokens: {stripped!r}"
        )

    if not _SINGLE_DATE_RE.match(date_raw):
        raise ElementParseError(
            f"Recap line's date should be 'ddMMMyy' (e.g. '16JUN26'): "
            f"{date_raw!r} in {stripped!r}"
        )

    if route != "ALL" and len(route) != 6:
        raise ElementParseError(
            f"Recap line's route should be exactly 6 characters (3+3) "
            f"if present: {route!r} in {stripped!r}"
        )

    return RecapSingleDateLine(
        raw=stripped,
        airline_code=m.group("airline"),
        flight_number=m.group("flight"),
        date_raw=date_raw,
        route=route,
    )