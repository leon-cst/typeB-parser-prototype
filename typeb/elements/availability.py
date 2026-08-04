"""
Availability line parser (AVN body).

REQ02 p.7-8: '<airline><flight> <rbd> <date> <board><off>', fields
SPACED, e.g. "AA800 F 01JUN CGKDPS". Not to be confused with booking
SEGMENT lines, which glue the equivalent fields together.
"""
from __future__ import annotations

import re

from typeb.elements.errors import ElementParseError
from typeb.model.elements import AvailabilityLine

_FIRST_TOKEN_RE = re.compile(r"^(?P<airline>[A-Z0-9]{2})(?P<flight>\d{1,4}[A-Z]?)$")
_DATE_RE = re.compile(r"^\d{2}[A-Z]{3}$")


def parse_availability_line(line: str) -> AvailabilityLine:
    stripped = line.strip()
    tokens = stripped.split()

    if len(tokens) != 4:
        raise ElementParseError(
            f"Availability line expected 4 space-separated tokens "
            f"(airline+flight, RBD, date, city pair), got {len(tokens)}: "
            f"{line!r}"
        )

    airline_flight, rbd, date_raw, city_pair = tokens

    m = _FIRST_TOKEN_RE.match(airline_flight)
    if not m:
        raise ElementParseError(
            f"Availability line's airline+flight token malformed: "
            f"{airline_flight!r} in {line!r}"
        )

    if len(rbd) != 1:
        raise ElementParseError(
            f"Availability line's RBD should be a single letter: "
            f"{rbd!r} in {line!r}"
        )

    if not _DATE_RE.match(date_raw):
        raise ElementParseError(
            f"Availability line's date should be 2-digit day + 3-letter "
            f"month (e.g. '01JUN'): {date_raw!r} in {line!r}"
        )

    if len(city_pair) != 6:
        raise ElementParseError(
            f"Availability line's city pair should be exactly 6 "
            f"characters (3+3): {city_pair!r} in {line!r}"
        )

    return AvailabilityLine(
        raw=stripped,
        airline_code=m.group("airline"),
        flight_number=m.group("flight"),
        reservation_booking_designator=rbd,
        date_raw=date_raw,
        board_point=city_pair[:3],
        off_point=city_pair[3:],
    )