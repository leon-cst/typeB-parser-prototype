"""
SEGMENT element parser (booking context).

REQ03 p.9-10: '<airline><flight><rbd><date> <board><off> <action><count>
[<dep> <arr>]', with the first field glued (airline + flight number + RBD
+ date all concatenated), e.g. "8G083F24SEP CGKDPS NN1 0910 1015".

Departure/arrival times are optional -- REQ03's examples show them
present for confirmed/waitlisted segments and can be absent depending on
status/bilateral agreement, so 2, or 0, trailing time tokens are both
accepted; anything else is treated as malformed rather than guessed at.
"""
from __future__ import annotations

import re

from typeb.elements.errors import ElementParseError
from typeb.model.elements import SegmentElement

_FIRST_TOKEN_RE = re.compile(
    r"^(?P<airline>[A-Z0-9]{2})(?P<flight>\d{2,4})(?P<rbd>[A-Z])(?P<date>\d{2}[A-Z]{3})$"
)
_ACTION_TOKEN_RE = re.compile(r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})$")
_TIME_RE = re.compile(r"^\d{4}$")


def parse_segment_element(line: str) -> SegmentElement:
    stripped = line.strip()
    tokens = stripped.split()

    if len(tokens) not in (3, 5):
        raise ElementParseError(
            f"SEGMENT line expected 3 tokens (no times) or 5 (with "
            f"departure+arrival times), got {len(tokens)}: {line!r}"
        )

    m = _FIRST_TOKEN_RE.match(tokens[0])
    if not m:
        raise ElementParseError(
            f"SEGMENT line's first token doesn't match "
            f"airline+flight+rbd+date shape: {tokens[0]!r} in {line!r}"
        )

    city_pair = tokens[1]
    if len(city_pair) != 6:
        raise ElementParseError(
            f"SEGMENT line's city pair should be exactly 6 characters "
            f"(3+3): {city_pair!r} in {line!r}"
        )

    action_match = _ACTION_TOKEN_RE.match(tokens[2])
    if not action_match:
        raise ElementParseError(
            f"SEGMENT line's action+count token malformed: "
            f"{tokens[2]!r} in {line!r}"
        )

    departure_time_raw: str | None = None
    arrival_time_raw: str | None = None
    if len(tokens) == 5:
        if not (_TIME_RE.match(tokens[3]) and _TIME_RE.match(tokens[4])):
            raise ElementParseError(
                f"SEGMENT line's time tokens should be 4 digits each "
                f"(HHMM): {tokens[3]!r}, {tokens[4]!r} in {line!r}"
            )
        departure_time_raw, arrival_time_raw = tokens[3], tokens[4]

    return SegmentElement(
        raw=stripped,
        airline_code=m.group("airline"),
        flight_number=m.group("flight"),
        reservation_booking_designator=m.group("rbd"),
        date_raw=m.group("date"),
        board_point=city_pair[:3],
        off_point=city_pair[3:],
        action_code=action_match.group("action"),
        number_in_party=int(action_match.group("count")),
        departure_time_raw=departure_time_raw,
        arrival_time_raw=arrival_time_raw,
    )