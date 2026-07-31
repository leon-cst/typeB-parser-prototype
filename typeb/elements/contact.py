"""
Shared email/DOB contact-info parsing.

Confirmed real: both SSR and OSI carry this identical shape --
REQ03 p.18 says SSR vs OSI marks whether the sender expects an
acknowledgement (SSR) or is just informing (OSI), not a structural
difference in the content itself. E.g.:

    OSI GA 1BAMBANG/MR E/BABANG@GMAIL.COM        (REQ03 p.23)
    SSR 8G 1ANGGARA/BAYIBUDI/MR E/BAYI1@GMAIL.COM (real message, no
                                                    4-letter SSR code)

This module only handles what comes AFTER the leading 'SSR'/'OSI' token
-- callers strip that themselves before calling in, since each caller
also needs to decide, using their own rules, whether this shape applies
at all before handing off here.
"""
from __future__ import annotations

from typeb.elements.errors import ElementParseError
from typeb.elements.name import parse_name_reference
from typeb.model.elements import DobElement, EmailContactElement


def is_email_shape(tokens: list[str]) -> bool:
    return bool(tokens) and tokens[-1].startswith("E/")


def is_dob_shape(tokens: list[str]) -> bool:
    return bool(tokens) and tokens[-1].startswith("DOB/")


def parse_email_contact(
    raw_line: str, source: str, tokens: list[str]
) -> EmailContactElement:
    """`tokens` = [airline, <name token>, email_token] -- the leading
    'SSR'/'OSI' token must already be stripped by the caller."""
    if len(tokens) < 3:
        raise ElementParseError(
            f"{source} email line too short, expected '<airline> <name> "
            f"E/<email>': {raw_line!r}"
        )
    airline_code = tokens[0]
    email_token = tokens[-1]
    name_tokens = tokens[1:-1]

    if len(name_tokens) != 1:
        raise ElementParseError(
            f"{source} email line expected exactly one name token "
            f"between the airline and the email field, got "
            f"{len(name_tokens)}: {raw_line!r}"
        )

    return EmailContactElement(
        raw=raw_line.strip(),
        source=source,
        airline_code=airline_code,
        name=parse_name_reference(name_tokens[0]),
        email=email_token[len("E/"):],
    )


def parse_dob(raw_line: str, source: str, tokens: list[str]) -> DobElement:
    """`tokens` = [airline, <name token>, dob_token] -- the leading
    'SSR'/'OSI' token must already be stripped by the caller."""
    if len(tokens) < 3:
        raise ElementParseError(
            f"{source} DOB line too short, expected '<airline> <name> "
            f"DOB/<date>': {raw_line!r}"
        )
    airline_code = tokens[0]
    dob_token = tokens[-1]
    name_tokens = tokens[1:-1]

    if len(name_tokens) != 1:
        raise ElementParseError(
            f"{source} DOB line expected exactly one name token between "
            f"the airline and the DOB field, got {len(name_tokens)}: "
            f"{raw_line!r}"
        )

    return DobElement(
        raw=raw_line.strip(),
        source=source,
        airline_code=airline_code,
        name=parse_name_reference(name_tokens[0]),
        date_of_birth_raw=dob_token[len("DOB/"):],
    )