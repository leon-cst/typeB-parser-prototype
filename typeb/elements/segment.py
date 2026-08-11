"""
SEGMENT element parser (booking context).
"""
from __future__ import annotations

import re

from typeb.elements.errors import ElementParseError
from typeb.model.elements import SegmentElement

_FIRST_TOKEN_RE = re.compile(
    r"^(?P<airline>[A-Z0-9]{2})(?P<flight>\d{2,4})(?P<rbd>[A-Z])"
    r"(?P<date>\d{2}[A-Z]{3}(?:\d{2})?)$"
)
_ACTION_TOKEN_RE = re.compile(r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})$")
_TIME_RE = re.compile(r"^\d{4}$")


_ARRIVAL_TIME_WITH_DAY_CHANGE_RE = re.compile(
    r"^(?P<time>\d{4})/(?P<sign>M?)(?P<offset>\d{1,2})$"
)


_GLUED_ACTION_COUNT_TIME_RE = re.compile(
    r"^(?P<action_count>[A-Z]{2}\d{1,3})/(?P<dep_time>\d{4})$"
)


def _split_glued_action_count_time(tokens: list[str]) -> list[str]:

    if len(tokens) not in (3, 4):
        return tokens

    action_idx = 2
    if action_idx >= len(tokens) or "/" not in tokens[action_idx]:
        return tokens

    m = _GLUED_ACTION_COUNT_TIME_RE.match(tokens[action_idx])
    if not m:
        return tokens

    split_head = tokens[:action_idx]
    split_action_dep = [m.group("action_count"), m.group("dep_time")]
    split_tail = tokens[action_idx + 1:]  # arrival time, if present
    return split_head + split_action_dep + split_tail


def parse_segment_element(line: str) -> SegmentElement:
    stripped = line.strip()
    tokens = _split_glued_action_count_time(stripped.split())

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
    arrival_day_offset: int | None = None
    if len(tokens) == 5:
        if not _TIME_RE.match(tokens[3]):
            raise ElementParseError(
                f"SEGMENT line's departure time should be 4 digits "
                f"(HHMM): {tokens[3]!r} in {line!r}"
            )
        departure_time_raw = tokens[3]

        arr_token = tokens[4]
        if _TIME_RE.match(arr_token):
            arrival_time_raw = arr_token
        else:
            day_change_match = _ARRIVAL_TIME_WITH_DAY_CHANGE_RE.match(arr_token)
            if not day_change_match:
                raise ElementParseError(
                    f"SEGMENT line's arrival time should be 4 digits "
                    f"(HHMM), optionally with a day-of-change indicator "
                    f"('/1' or '/M1'): {arr_token!r} in {line!r}"
                )
            arrival_time_raw = day_change_match.group("time")
            offset = int(day_change_match.group("offset"))
            arrival_day_offset = (
                -offset if day_change_match.group("sign") == "M" else offset
            )

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
        arrival_day_offset=arrival_day_offset,
    )


def render_segment_element(segment: SegmentElement) -> str:
    first = (
        f"{segment.airline_code}{segment.flight_number}"
        f"{segment.reservation_booking_designator}{segment.date_raw}"
    )
    city_pair = f"{segment.board_point}{segment.off_point}"
    action = f"{segment.action_code}{segment.number_in_party}"
    tokens = [first, city_pair, action]
    if segment.departure_time_raw and segment.arrival_time_raw:
        arrival = segment.arrival_time_raw
        if segment.arrival_day_offset is not None:
            offset = segment.arrival_day_offset
            arrival += f"/M{-offset}" if offset < 0 else f"/{offset}"
        tokens += [segment.departure_time_raw, arrival]
    return " ".join(tokens)