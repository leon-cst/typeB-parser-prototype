from __future__ import annotations

import re

from typeb.elements.contact import is_dob_shape, is_email_shape, parse_dob, parse_email_contact
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_reference
from typeb.model.elements import (
    SsrChildOrInfantFlagElement,
    SsrFoidElement,
    SsrGroupElement,
    SsrRecordLocatorElement,
    SsrTicketNumberElement,
)

_NON_AUTOMATED_RE = re.compile(
    r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})/(?P<text>[^-]+)"
    r"(?:-(?P<name>.+))?$"
)

_ACTION_COUNT_RE = re.compile(r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})$")


def _parse_ssr_foid(line: str, tokens: list[str]) -> SsrFoidElement:
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR FOID line too short, expected 'SSR FOID <airline> "
            f"<action><count>/<text>[-<n>]': {line!r}"
        )
    airline_code = tokens[2]
    remainder = " ".join(tokens[3:])

    m = _NON_AUTOMATED_RE.match(remainder)
    if not m:
        raise ElementParseError(
            f"SSR FOID's action/count/structured-text portion malformed "
            f"(expected '<action><count>/<text>[-<n>]'): {remainder!r} in {line!r}"
        )

    name = parse_name_reference(m.group("name")) if m.group("name") else None

    return SsrFoidElement(
        raw=line.strip(),
        airline_code=airline_code,
        action_code=m.group("action"),
        number_in_party=int(m.group("count")),
        structured_text=m.group("text"),
        name=name,
    )


def _parse_ssr_child_or_infant_flag(line: str, tokens: list[str]):
    if len(tokens) != 4:
        raise ElementParseError(
            f"SSR {tokens[1]} line expected exactly 4 tokens "
            f"('SSR', code, airline, name), got {len(tokens)}. This shape "
            f"has no official spec format to check against: {line!r}"
        )
    return SsrChildOrInfantFlagElement(
        raw=line.strip(),
        ssr_code=tokens[1],
        airline_code=tokens[2],
        name=parse_name_reference(tokens[3]),
    )


def _split_automated_ssr(line: str, tokens: list[str], code: str):
    """Shared splitter for the REQ03 section 12 automated shape:

        SSR <code> <airline> [<action><count>] <segment ref> [-<name>] .<text>

    The segment reference is left undecomposed -- across REQ03's own
    examples it appears glued ("NRTLAX0123Y21DEC"), part-spaced
    ("NRTLAX 0006Y21DEC") and fully spaced ("DFWMIA 0614 Y 15AUG"), with
    no stated rule for which applies. Action code and count are optional
    (section 12 makes them optional for some codes; section 18's CONTOH-2
    omits them for TKNE too).
    """
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR {code} line too short, expected at least "
            f"'SSR {code} <airline> <segment ref>.<text>': {line!r}"
        )

    airline_code = tokens[2]
    rest = tokens[3:]

    action_code = number_in_party = None
    m = _ACTION_COUNT_RE.match(rest[0])
    if m and len(rest) > 1:
        action_code = m.group("action")
        number_in_party = int(m.group("count"))
        rest = rest[1:]

    remainder = " ".join(rest)
    if "." not in remainder:
        raise ElementParseError(
            f"SSR {code} line missing the '.' separating the segment "
            f"reference from its trailing value: {line!r}"
        )
    left, trailing_text = remainder.rsplit(".", 1)
    if not trailing_text:
        raise ElementParseError(
            f"SSR {code} line has nothing after the '.': {line!r}"
        )

    segment_reference_raw, _, name_token = left.partition("-")
    segment_reference_raw = segment_reference_raw.strip()
    if not segment_reference_raw:
        raise ElementParseError(
            f"SSR {code} line missing its segment reference: {line!r}"
        )

    name = parse_name_reference(name_token.strip()) if name_token.strip() else None

    return airline_code, action_code, number_in_party, segment_reference_raw, name, trailing_text


def _parse_ssr_tkne(line: str, tokens: list[str]) -> SsrTicketNumberElement:
    airline, action, count, segref, name, text = _split_automated_ssr(line, tokens, "TKNE")
    return SsrTicketNumberElement(
        raw=line.strip(),
        airline_code=airline,
        action_code=action,
        number_in_party=count,
        segment_reference_raw=segref,
        name=name,
        ticket_number_raw=text,
    )


def _parse_ssr_rloc(line: str, tokens: list[str]) -> SsrRecordLocatorElement:
    airline, action, count, segref, name, text = _split_automated_ssr(line, tokens, "RLOC")
    return SsrRecordLocatorElement(
        raw=line.strip(),
        airline_code=airline,
        action_code=action,
        number_in_party=count,
        segment_reference_raw=segref,
        name=name,
        record_locator=text,
    )


def _parse_ssr_grps(line: str, tokens: list[str]) -> SsrGroupElement:
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR GRPS line too short, expected 'SSR GRPS <airline> "
            f"<structured text> [<group name>]': {line!r}"
        )
    return SsrGroupElement(
        raw=line.strip(),
        airline_code=tokens[2],
        structured_text=tokens[3],
        group_name=" ".join(tokens[4:]) or None,
    )


_SSR_HANDLERS = {
    "FOID": _parse_ssr_foid,
    "INFT": _parse_ssr_child_or_infant_flag,
    "CHLD": _parse_ssr_child_or_infant_flag,
    "TKNE": _parse_ssr_tkne,
    "RLOC": _parse_ssr_rloc,
    "GRPS": _parse_ssr_grps,
}


def parse_ssr_line(line: str):
    stripped = line.strip()
    tokens = stripped.split()

    if len(tokens) < 2 or tokens[0] != "SSR":
        raise ElementParseError(f"Not an SSR line: {line!r}")

    ssr_code = tokens[1]
    handler = _SSR_HANDLERS.get(ssr_code)
    if handler is not None:
        return handler(stripped, tokens)

    rest_tokens = tokens[1:]
    if is_email_shape(rest_tokens):
        return parse_email_contact(stripped, "SSR", rest_tokens)
    if is_dob_shape(rest_tokens):
        return parse_dob(stripped, "SSR", rest_tokens)

    raise UnrecognizedElementError(
        f"No parser implemented yet for SSR code {ssr_code!r} -- "
        f"currently supported codes: {sorted(_SSR_HANDLERS)}, plus the "
        f"code-less email/DOB shape. Line: {line!r}"
    )