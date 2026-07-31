"""
NAME element parser.

REQ03 section 9 "Name Element" (p.9-10), reconstructed from the spec's
worked examples (surname/title punctuation is deliberate, not typos):

    1. "MR. JEAN DUVAL"                 -> 1DUVAL/JEANMR
    2. "MR. EDWARD CHARLES JONES"       -> 1JONES/EDWARDCHARLES/MR
    3. "MISS. DUVALIER"                 -> 1DUVALIER/MISS
    4. "E FORD, B FORD, C FORD"         -> 3FORD/E/B/C
    5. "MRS. B KHOWRY"                  -> 1KHOWRY/MRS

The rule these examples encode: a NAME line is
'<number in party><surname>/<given-name tokens...>'. The number of
given-name tokens is either exactly `number_in_party` (one per person;
the title is glued onto the LAST person's token if present, e.g. "JEANMR"
-- and if that whole token IS a title with nothing else, that person has
no given name at all, e.g. example 3/5), or exactly `number_in_party + 1`
(everyone has a given name, and the LAST person's title is instead its
own separate final token, e.g. example 2's "EDWARDCHARLES"+"MR"). No
other token count matches the documented grammar -- anything else raises
rather than guessing (this is what catches out-of-spec real-world
variants, e.g. a line packing two different surnames under one
number-in-party, which does NOT fit either accepted shape).

Only the LAST person in a party can carry a title -- that's the only
slot the format provides. Earlier people in a group are always
given-name-only (example 4's E and B are plain; C is last and still ends
up untitled only because "C" doesn't end with any known title -- see
_split_glued_title).

Single-letter initials being silently dropped (example 5: "B" from
"MRS. B KHOWRY" simply never appears) happens upstream, when the message
is composed -- there is nothing for this parser to detect or reconstruct;
by the time text reaches us, "1KHOWRY/MRS" is already complete and final.

NOT implemented here (explicitly deferred, not silently ignored):
  - Continuation lines (a NAME line exceeding 69 chars repeats the
    leading number + group name on the next physical line)
  - EXST (extra seat) / CBBG (cabin bag) / JR / SR occupying the title
    slot
  - Double-letter / space / hyphen collapsing in names (e.g. "ALI BABA"
    -> "ALIBABA") -- this alters content, not just formatting, and isn't
    implemented until the exact collapsing rule is confirmed
"""
from __future__ import annotations

import re

from typeb.elements.errors import ElementParseError
from typeb.model.elements import NameElement, NameReference, Person
from typeb.tables import loader

_LEADING_DIGITS_RE = re.compile(r"^(\d{1,3})(.*)$")
_OPTIONAL_LEADING_DIGITS_RE = re.compile(r"^(\d{1,3})?(.*)$")

# REQ03 p.11: EXST (extra seat) / CBBG (cabin baggage occupying its own
# seat) occupy a trailing slot on the NAME line, incrementing
# number_in_party for a "phantom seat" that isn't a real person. Only
# ONE modifier per line is evidenced (the DOOLEY/EXST example) -- support
# for stacking more than one isn't built since there's nothing to verify
# it against.
_SEAT_MODIFIER_KEYWORDS = {"EXST", "CBBG"}


def _known_titles_longest_first() -> list[str]:
    return sorted(loader.name_title_codes().keys(), key=len, reverse=True)


def _split_glued_title(token: str) -> tuple[str | None, str | None]:
    """Returns (given_name, title). If the whole token IS a known title
    (nothing else attached), given_name is None -- REQ03 examples 3/5:
    no first/middle name was given, the title occupies the whole slot.
    If the token ends with a known title and has more before it, splits
    them (example 1: "JEANMR" -> "JEAN" + "MR"). Longest-title-first so
    "BAMBANGMRS" isn't wrongly split by matching the shorter "MR" first.
    If nothing matches, returns the token unchanged with title=None."""
    for title in _known_titles_longest_first():
        if token == title:
            return None, title
        if token.endswith(title) and len(token) > len(title):
            return token[: -len(title)], title
    return token, None


def parse_name_element(line: str) -> NameElement:
    stripped = line.strip()

    m = _LEADING_DIGITS_RE.match(stripped)
    if not m:
        raise ElementParseError(
            f"NAME line must start with 1-3 digit number in party: {line!r}"
        )
    number_in_party = int(m.group(1))
    rest = m.group(2)

    if not rest:
        raise ElementParseError(
            f"NAME line has a number in party but nothing after it: {line!r}"
        )

    if "/" not in rest:
        # Group-placeholder line, e.g. "6SEAMEN" -- no individual names
        # known yet.
        return NameElement(
            raw=stripped,
            number_in_party=number_in_party,
            surname=rest,
            people=[],
            is_group_placeholder=True,
            seat_modifiers=[],
        )

    parts = rest.split("/")
    surname, trailing = parts[0], parts[1:]

    if not surname:
        raise ElementParseError(f"NAME line missing surname before '/': {line!r}")
    if not trailing:
        raise ElementParseError(
            f"NAME line has '/' but no given-name/title tokens after it: {line!r}"
        )

    # Strip a trailing seat modifier (EXST/CBBG) before doing anything
    # else -- it consumes one slot of number_in_party without describing
    # a real person, so the party-size math below needs to account for
    # it separately (see REQ03 p.11's DOOLEY/EXST example).
    seat_modifiers: list[str] = []
    if trailing and trailing[-1] in _SEAT_MODIFIER_KEYWORDS:
        seat_modifiers.append(trailing.pop())

    effective_party_count = number_in_party - len(seat_modifiers)
    if effective_party_count < 1:
        raise ElementParseError(
            f"NAME line has more seat-modifier tokens ({seat_modifiers}) "
            f"than number_in_party={number_in_party} can account for: {line!r}"
        )

    if not trailing:
        raise ElementParseError(
            f"NAME line has a seat modifier ({seat_modifiers}) but no "
            f"given-name/title tokens before it: {line!r}"
        )

    known_titles = set(loader.name_title_codes().keys())
    people: list[Person] = []

    if len(trailing) == effective_party_count + 1:
        # Title is its own separate final token (REQ03 example 2).
        given_name_tokens, title_token = trailing[:-1], trailing[-1]
        if title_token not in known_titles:
            raise ElementParseError(
                f"NAME line has {effective_party_count + 1} given-name/title "
                f"tokens after the surname (one more than the effective "
                f"party count of {effective_party_count}), which only fits "
                f"the grammar if the final token is a standalone title -- "
                f"got {title_token!r} in {line!r}"
            )
        for i, token in enumerate(given_name_tokens):
            is_last = i == len(given_name_tokens) - 1
            people.append(
                Person(given_name=token, title=title_token if is_last else None)
            )

    elif len(trailing) == effective_party_count:
        # One token per person; the LAST person's token may have a
        # title glued on (or be a title with no given name at all).
        for i, token in enumerate(trailing):
            is_last = i == len(trailing) - 1
            if is_last:
                given_name, title = _split_glued_title(token)
            else:
                given_name, title = token, None
            people.append(Person(given_name=given_name, title=title))

    else:
        raise ElementParseError(
            f"NAME line has {len(trailing)} given-name/title tokens after "
            f"the surname (after removing any seat modifier), but the "
            f"effective party count is {effective_party_count} -- the "
            f"documented grammar (REQ03 section 9) only accounts for "
            f"{effective_party_count} tokens (title glued onto or "
            f"replacing the last person's token) or "
            f"{effective_party_count + 1} (title as its own separate "
            f"final token). Not confidently handled -- refusing to guess "
            f"rather than silently mis-parsing a possibly out-of-spec "
            f"variant: {line!r}"
        )

    return NameElement(
        raw=stripped,
        number_in_party=number_in_party,
        surname=surname,
        people=people,
        is_group_placeholder=False,
        seat_modifiers=seat_modifiers,
    )


def parse_name_reference(token: str) -> NameReference:
    """Parse a name as embedded in an SSR or OSI line -- always exactly
    one person, unlike parse_name_element's party-of-N grammar. See
    NameReference's docstring for why this is a separate function rather
    than a special case of parse_name_element: the leading digit here
    (when present at all) doesn't count anything about this reference."""
    stripped = token.strip()

    m = _OPTIONAL_LEADING_DIGITS_RE.match(stripped)
    leading_number = int(m.group(1)) if m.group(1) else None
    rest = m.group(2)

    if not rest or "/" not in rest:
        raise ElementParseError(
            f"Name reference malformed, expected "
            f"'[N]SURNAME/GIVEN[/TITLE]': {token!r}"
        )

    parts = rest.split("/")
    surname, trailing = parts[0], parts[1:]

    if not surname:
        raise ElementParseError(f"Name reference missing surname: {token!r}")
    if not trailing:
        raise ElementParseError(
            f"Name reference missing given name/title after surname: {token!r}"
        )

    known_titles = set(loader.name_title_codes().keys())

    if len(trailing) == 1:
        given_name, title = _split_glued_title(trailing[0])
    elif len(trailing) == 2:
        given_name, title = trailing[0], trailing[1]
        if title not in known_titles:
            raise ElementParseError(
                f"Name reference has 2 tokens after the surname, which "
                f"only fits the grammar if the second is a standalone "
                f"title -- got {title!r} in {token!r}"
            )
    else:
        raise ElementParseError(
            f"Name reference has {len(trailing)} tokens after the "
            f"surname -- expected 1 (given name, title optionally glued) "
            f"or 2 (given name + separate title token): {token!r}"
        )

    return NameReference(
        raw=stripped,
        leading_number=leading_number,
        surname=surname,
        given_name=given_name,
        title=title,
    )