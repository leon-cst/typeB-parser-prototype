"""
RVR recap request line parser.

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