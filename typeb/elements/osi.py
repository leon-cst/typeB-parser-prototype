from __future__ import annotations

from typeb.elements.contact import is_dob_shape, is_email_shape, parse_dob, parse_email_contact
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_reference
from typeb.model.elements import (
    OsiContactAddressElement,
    OsiPassengerTypeFlagElement,
    OsiRecordLocatorElement,
)


def _parse_osi_contact_address(line: str, tokens: list[str]) -> OsiContactAddressElement:
    if len(tokens) < 4:
        raise ElementParseError(
            f"OSI contact-address line too short, expected 'OSI <airline> "
            f"<CTC?> <detail>...': {line!r}"
        )
    return OsiContactAddressElement(
        raw=line.strip(),
        airline_code=tokens[1],
        action_code=tokens[2],
        detail=" ".join(tokens[3:]),
    )


def _parse_osi_passenger_type_flag(line: str, tokens: list[str]):
    if len(tokens) != 5 or tokens[3] not in ("CHD", "INF"):
        raise ElementParseError(
            f"OSI passenger-type flag line expected exactly 5 tokens "
            f"('OSI', airline, an unexplained field, 'CHD' or 'INF', "
            f"name), e.g. 'OSI YY 1 CHD 1MARSH/E': {line!r}"
        )
    return OsiPassengerTypeFlagElement(
        raw=line.strip(),
        airline_code=tokens[1],
        unexplained_field=tokens[2],
        passenger_type=tokens[3],
        name=parse_name_reference(tokens[4]),
    )


def _parse_osi_record_locator(line: str, tokens: list[str]):
    # REQ03 section 17: "OSI NH RLOC NH CPNRNH"
    if len(tokens) != 5:
        raise ElementParseError(
            f"OSI RLOC line expected exactly 5 tokens ('OSI', airline, "
            f"'RLOC', airline, record locator), got {len(tokens)}: {line!r}"
        )
    return OsiRecordLocatorElement(
        raw=line.strip(),
        airline_code=tokens[1],
        record_locator_airline=tokens[3],
        record_locator=tokens[4],
    )


def parse_osi_line(line: str):
    stripped = line.strip()
    tokens = stripped.split()

    if len(tokens) < 3 or tokens[0] != "OSI":
        raise ElementParseError(f"Not an OSI line: {line!r}")

    rest_tokens = tokens[1:]

    if is_email_shape(rest_tokens):
        return parse_email_contact(stripped, "OSI", rest_tokens)
    if is_dob_shape(rest_tokens):
        return parse_dob(stripped, "OSI", rest_tokens)
    if "RLOC" in tokens:
        return _parse_osi_record_locator(stripped, tokens)
    if "CHD" in tokens or "INF" in tokens:
        return _parse_osi_passenger_type_flag(stripped, tokens)
    if len(tokens) >= 3 and tokens[2].startswith("CTC"):
        return _parse_osi_contact_address(stripped, tokens)

    raise UnrecognizedElementError(
        f"No parser implemented yet for this OSI shape (recognized: "
        f"email 'E/...', DOB 'DOB/...', 'RLOC', passenger-type flag "
        f"'CHD'/'INF', contact address 'CTC*'): {line!r}"
    )