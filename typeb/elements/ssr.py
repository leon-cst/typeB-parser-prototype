"""
SSR element parser.

REQ03 section 12 (p.18-22) gives two official formats:

  Automated:      SSR <code> <airline> <action><count> <segment ref glued>[-<name>][.<free text>]
  Non-automated:  SSR <code> <airline> <action><count>/<structured text>[-<name>][.<free text>]

Only the non-automated shape is built here (FOID), confirmed against a
real message field-for-field. The automated format (NSST, SMSW, BIKE,
meal codes, etc.) is real and well-specified but not needed for current
scope and not built yet.

SSR INFT / SSR CHLD don't match either official format -- REQ03 section
9 mentions both codes exist but never gives a worked example of their
wire format, which is a real gap in the source document. Built directly
against a real message's shape instead (see SsrChildOrInfantFlagElement's
docstring).

A FOURTH shape, confirmed real: SSR can carry email/DOB contact info with
NO 4-letter code at all -- "SSR 8G 1ANGGARA/BAYIBUDI/MR E/BAYI1@GMAIL.COM"
-- identical in content to the OSI email/DOB shape, differing only in
whether the sender wants an acknowledgement (SSR) or not (OSI). This is
why the email/DOB parsing lives in typeb.elements.contact, shared by both
dispatchers rather than duplicated.

Dispatch order matters: a known 4-letter SSR code is checked FIRST, and
only once that's ruled out does this fall back to checking the code-less
email/DOB shape -- airline codes are always 2-3 characters, never 4, so
there's no real ambiguity between "this is a code" and "this is an
airline code," but checking code first is the more conservative order.
An SSR code with no implemented parser raises clearly rather than
silently skipping or mis-parsing it -- see ElementParseError message.
"""
from __future__ import annotations

import re

from typeb.elements.contact import is_dob_shape, is_email_shape, parse_dob, parse_email_contact
from typeb.elements.errors import ElementParseError, UnrecognizedElementError
from typeb.elements.name import parse_name_reference
from typeb.model.elements import SsrChildOrInfantFlagElement, SsrFoidElement

# Non-automated format (REQ03 p.21): action+count glued, then '/',
# then structured text, then optionally '-' + name.
_NON_AUTOMATED_RE = re.compile(
    r"^(?P<action>[A-Z]{2})(?P<count>\d{1,3})/(?P<text>[^-]+)"
    r"(?:-(?P<name>.+))?$"
)


def _parse_ssr_foid(line: str, tokens: list[str]) -> SsrFoidElement:
    if len(tokens) < 4:
        raise ElementParseError(
            f"SSR FOID line too short, expected 'SSR FOID <airline> "
            f"<action><count>/<text>[-<name>]': {line!r}"
        )
    airline_code = tokens[2]
    remainder = " ".join(tokens[3:])

    m = _NON_AUTOMATED_RE.match(remainder)
    if not m:
        raise ElementParseError(
            f"SSR FOID's action/count/structured-text portion malformed "
            f"(expected '<action><count>/<text>[-<name>]'): "
            f"{remainder!r} in {line!r}"
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


def _parse_ssr_child_or_infant_flag(
    line: str, tokens: list[str]
) -> SsrChildOrInfantFlagElement:
    if len(tokens) != 4:
        raise ElementParseError(
            f"SSR {tokens[1]} line expected exactly 4 tokens "
            f"('SSR', code, airline, name), got {len(tokens)}. This shape "
            f"has no official spec format to check against (REQ03 "
            f"section 9 names the code but gives no worked example), so "
            f"only the exact real-world shape seen so far is accepted: "
            f"{line!r}"
        )
    return SsrChildOrInfantFlagElement(
        raw=line.strip(),
        ssr_code=tokens[1],
        airline_code=tokens[2],
        name=parse_name_reference(tokens[3]),
    )


_SSR_HANDLERS = {
    "FOID": _parse_ssr_foid,
    "INFT": _parse_ssr_child_or_infant_flag,
    "CHLD": _parse_ssr_child_or_infant_flag,
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

    # Not a known 4-letter code -- check the code-less email/DOB shape
    # before giving up (see module docstring).
    rest_tokens = tokens[1:]  # everything after "SSR"
    if is_email_shape(rest_tokens):
        return parse_email_contact(stripped, "SSR", rest_tokens)
    if is_dob_shape(rest_tokens):
        return parse_dob(stripped, "SSR", rest_tokens)

    raise UnrecognizedElementError(
        f"No parser implemented yet for SSR code {ssr_code!r} -- "
        f"currently supported codes: {sorted(_SSR_HANDLERS)}, plus the "
        f"code-less email/DOB shape. Line: {line!r}"
    )