from __future__ import annotations

import re

from typeb.elements.contact import is_dob_shape, is_email_shape, parse_dob, parse_email_contact
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_element, parse_name_reference
from typeb.model.elements import (
    AutomatedSsrElement,
    SsrChildOrInfantFlagElement,
    SsrFoidElement,
    SsrGroupElement,
    SsrGroupFareElement,
    SsrGroupSeatElement,
    SsrRecordLocatorElement,
    SsrTicketingTimeLimitElement,
    SsrTicketNumberElement,
)

_NON_AUTOMATED_RE = re.compile(
    r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})/(?P<text>[^-]+)"
    r"(?:-(?P<name>.+))?$"
)

_ACTION_COUNT_RE = re.compile(r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})$")


def _parse_name_token_flexibly(name_token: str):
    """A name attached to an SSR/OSI line via '-' is usually a single
    person (REQ03's numbered field tables only ever show one), but
    section 16's group examples attach a full multi-person
    shared-surname reference the same way (e.g.
    "-5ARDMORE/BOB/SUE/TIM/TOM/TONY"). Try the strict single-person
    shape first; only fall back to the richer NAME grammar if that
    fails, so this never silently accepts something looser than
    intended for the common case."""
    try:
        return parse_name_reference(name_token)
    except ElementParseError:
        return parse_name_element(name_token)


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


def _split_automated_ssr(
    line: str, tokens: list[str], code: str, *, text_required: bool = True
):
    """Shared splitter for the REQ03 section 12 automated shape:

        SSR <code> <airline> [<action><count>] <segment ref> [-<name>] [.<text>]

    The segment reference is left undecomposed -- across REQ03's own
    examples it appears glued ("NRTLAX0123Y21DEC"), part-spaced
    ("NRTLAX 0006Y21DEC") and fully spaced ("DFWMIA 0614 Y 15AUG"), with
    no stated rule for which applies. Action code and count are optional
    (section 12 makes them optional for some codes; section 18's CONTOH-2
    omits them for TKNE too). The dot-prefixed free text is itself
    optional per REQ03's own automated-format table (item 12, "if
    applicable") -- text_required=True preserves the stricter behavior
    TKNE/RLOC always need (both always carry a real trailing value).
    """
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR {code} line too short, expected at least "
            f"'SSR {code} <airline> <segment ref>': {line!r}"
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

    if "." in remainder:
        left, trailing_text = remainder.rsplit(".", 1)
        if not trailing_text:
            raise ElementParseError(
                f"SSR {code} line has nothing after the '.': {line!r}"
            )
    elif text_required:
        raise ElementParseError(
            f"SSR {code} line missing the '.' separating the segment "
            f"reference from its trailing value: {line!r}"
        )
    else:
        left, trailing_text = remainder, None

    segment_reference_raw, _, name_token = left.partition("-")
    segment_reference_raw = segment_reference_raw.strip()
    if not segment_reference_raw:
        raise ElementParseError(
            f"SSR {code} line missing its segment reference: {line!r}"
        )

    name = _parse_name_token_flexibly(name_token.strip()) if name_token.strip() else None


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


def _parse_ssr_grpf(line: str, tokens: list[str]) -> SsrGroupFareElement:
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR GRPF line too short, expected 'SSR GRPF <airline> "
            f"<status code> [<detail>...]': {line!r}"
        )
    return SsrGroupFareElement(
        raw=line.strip(),
        airline_code=tokens[2],
        status_code=tokens[3],
        detail=" ".join(tokens[4:]) or None,
    )


def _parse_ssr_gpst(line: str, tokens: list[str]) -> SsrGroupSeatElement:
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR GPST line too short, expected 'SSR GPST <airline> "
            f"<action><count> <segment ref>': {line!r}"
        )

    # Segment reference may be space-separated from action+count (per
    # section 16's "NN30 JFKSTL0209Y11AUG" example) or fully glued onto
    # it (real message traffic: "NN25JFKSTL0209Y11AUG") -- same
    # glued-vs-spaced bilateral variance already handled for SEGMENT.
    m = _ACTION_COUNT_RE.match(tokens[3])
    if m:
        segment_reference_raw = " ".join(tokens[4:])
    else:
        m = re.match(r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})(?P<rest>[A-Z0-9].*)$", tokens[3])
        if not m:
            raise ElementParseError(
                f"SSR GPST's action+count token malformed: {tokens[3]!r} in {line!r}"
            )
        segment_reference_raw = " ".join([m.group("rest")] + tokens[4:])

    if not segment_reference_raw:
        raise ElementParseError(
            f"SSR GPST line missing its segment reference: {line!r}"
        )
    return SsrGroupSeatElement(
        raw=line.strip(),
        airline_code=tokens[2],
        action_code=m.group("action"),
        number_in_party=int(m.group("count")),
        segment_reference_raw=segment_reference_raw,
    )


def _parse_ssr_tktl(line: str, tokens: list[str]) -> SsrTicketingTimeLimitElement:
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR TKTL line too short: {line!r}"
        )
    status_and_city = tokens[3]
    remainder = " ".join(tokens[4:])

    if "//" in status_and_city:
        status_code, city_code = status_and_city.split("//", 1)
        if not status_code or not city_code or not remainder:
            raise ElementParseError(
                f"SSR TKTL removal shape expected "
                f"'<status>//<city> <free text>': {line!r}"
            )
        return SsrTicketingTimeLimitElement(
            raw=line.strip(),
            airline_code=tokens[2],
            status_code=status_code,
            city_code=city_code,
            time_raw=None,
            date_raw=None,
            removal_note=remainder,
        )

    if "/" in status_and_city:
        status_code, city_code = status_and_city.split("/", 1)
        time_date_m = re.match(r"^(?P<time>\d{4})/(?P<date>\d{2}[A-Z]{3})$", remainder)
        if not status_code or not city_code or not time_date_m:
            raise ElementParseError(
                f"SSR TKTL set shape expected "
                f"'<status>/<city> <time>/<date>': {line!r}"
            )
        return SsrTicketingTimeLimitElement(
            raw=line.strip(),
            airline_code=tokens[2],
            status_code=status_code,
            city_code=city_code,
            time_raw=time_date_m.group("time"),
            date_raw=time_date_m.group("date"),
            removal_note=None,
        )

    raise ElementParseError(
        f"SSR TKTL line doesn't match either recognized shape "
        f"(set: '<status>/<city> <time>/<date>', remove: "
        f"'<status>//<city> <free text>'): {line!r}"
    )


def _parse_ssr_automated_generic(line: str, tokens: list[str]) -> AutomatedSsrElement:
    code = tokens[1]
    airline, action, count, segref, name, text = _split_automated_ssr(
        line, tokens, code, text_required=False
    )
    return AutomatedSsrElement(
        raw=line.strip(),
        ssr_code=code,
        airline_code=airline,
        action_code=action,
        number_in_party=count,
        segment_reference_raw=segref,
        name=name,
        free_text=text,
    )


# REQ03 section 12's own automated-format worked examples (LSML, NSST,
# SMSW) plus VGML/BSCT/OTHS from other worked examples elsewhere in the
# document -- codes explicitly evidenced as following this exact shape.
# Deliberately NOT a catch-all for any unrecognized 4-letter code: an
# SSR code not in this set and not in _SSR_HANDLERS still raises
# UnrecognizedElementError rather than being guessed at.
_AUTOMATED_FORMAT_CODES = {"LSML", "NSST", "SMSW", "VGML", "BSCT", "OTHS"}


_SSR_HANDLERS = {
    "FOID": _parse_ssr_foid,
    "INFT": _parse_ssr_child_or_infant_flag,
    "CHLD": _parse_ssr_child_or_infant_flag,
    "TKNE": _parse_ssr_tkne,
    "RLOC": _parse_ssr_rloc,
    "GRPS": _parse_ssr_grps,
    "GRPF": _parse_ssr_grpf,
    "GPST": _parse_ssr_gpst,
    "TKTL": _parse_ssr_tktl,
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

    if ssr_code in _AUTOMATED_FORMAT_CODES:
        return _parse_ssr_automated_generic(stripped, tokens)

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