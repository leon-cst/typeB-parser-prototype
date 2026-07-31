"""
OSI element parser.

REQ03 section 13 (p.22-23): 'OSI <airline> <service info...> [<name>]'.
Unlike SSR, there's no fixed "code" token position -- the shape varies by
sub-type. Dispatches by inspecting the line's tokens rather than a fixed
position:

  - last token starts with "E/"   -> email (shared with SSR, see
    typeb.elements.contact)
  - last token starts with "DOB/" -> date of birth (shared with SSR)
  - "CHD" or "INF" appears as a standalone token -> passenger-type flag,
    OSI-only (p.22's official examples: "OSI YY 1 CHD 1MARSH/E")

Only these three sub-types are built. TKNO (ticket number) and general
contact-info codes (A/B/F/H/M/T beyond email) are documented but not
implemented yet.
"""
from __future__ import annotations

from typeb.elements.contact import is_dob_shape, is_email_shape, parse_dob, parse_email_contact
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_reference
from typeb.model.elements import OsiPassengerTypeFlagElement


def _parse_osi_passenger_type_flag(
    line: str, tokens: list[str]
) -> OsiPassengerTypeFlagElement:
    if len(tokens) != 5 or tokens[3] not in ("CHD", "INF"):
        raise ElementParseError(
            f"OSI passenger-type flag line expected exactly 5 tokens "
            f"('OSI', airline, an unexplained field, 'CHD' or 'INF', "
            f"name) -- REQ03 p.22's own examples all have this shape, "
            f"e.g. 'OSI YY 1 CHD 1MARSH/E': {line!r}"
        )
    return OsiPassengerTypeFlagElement(
        raw=line.strip(),
        airline_code=tokens[1],
        unexplained_field=tokens[2],
        passenger_type=tokens[3],
        name=parse_name_reference(tokens[4]),
    )


def parse_osi_line(line: str):
    stripped = line.strip()
    tokens = stripped.split()

    if len(tokens) < 3 or tokens[0] != "OSI":
        raise ElementParseError(f"Not an OSI line: {line!r}")

    rest_tokens = tokens[1:]  # everything after "OSI"

    if is_email_shape(rest_tokens):
        return parse_email_contact(stripped, "OSI", rest_tokens)
    if is_dob_shape(rest_tokens):
        return parse_dob(stripped, "OSI", rest_tokens)
    if "CHD" in tokens or "INF" in tokens:
        return _parse_osi_passenger_type_flag(stripped, tokens)

    raise UnrecognizedElementError(
        f"No parser implemented yet for this OSI shape (recognized: "
        f"email 'E/...', DOB 'DOB/...', passenger-type flag 'CHD'/'INF'): "
        f"{line!r}"
    )