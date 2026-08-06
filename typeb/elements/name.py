from __future__ import annotations

import re

from typeb.elements.errors import ElementParseError
from typeb.model.elements import NameElement, NameReference, Person
from typeb.tables import loader

_LEADING_DIGITS_RE = re.compile(r"^(\d{1,3})(.*)$")
_OPTIONAL_LEADING_DIGITS_RE = re.compile(r"^(\d{1,3})?(.*)$")
_SEAT_MODIFIER_KEYWORDS = {"EXST", "CBBG"} # expand as needed


def _known_titles_longest_first() -> list[str]:
    return sorted(loader.name_title_codes().keys(), key=len, reverse=True)


def _split_glued_title(token: str) -> tuple[str | None, str | None]:
    for title in _known_titles_longest_first():
        if token == title:
            return None, title
        if token.endswith(title) and len(token) > len(title):
            return token[: -len(title)], title
    return token, None


def _try_parse_shared_surname(
    trailing: list[str], effective_party_count: int, known_titles: set[str]
) -> list[Person] | None:
    if len(trailing) == effective_party_count + 1:
        given_name_tokens, title_token = trailing[:-1], trailing[-1]
        if title_token not in known_titles:
            return None
        people: list[Person] = []
        for i, token in enumerate(given_name_tokens):
            is_last = i == len(given_name_tokens) - 1
            people.append(
                Person(given_name=token, title=title_token if is_last else None)
            )
        return people

    if len(trailing) == effective_party_count:
        people = []
        for token in trailing:
            given_name, title = _split_glued_title(token)
            people.append(Person(given_name=given_name, title=title))
        return people

    return None


def _chunk_to_person(chunk: list[str], title: str | None) -> Person:
    surname_token, *given_tokens = chunk
    given_name = " ".join(given_tokens) if given_tokens else None
    return Person(surname=surname_token, given_name=given_name, title=title)


def _try_parse_distinct_surnames(
    full_sequence: list[str], effective_party_count: int
) -> list[Person] | None:
    people: list[Person] = []
    chunk: list[str] = []

    for token in full_sequence:
        leftover, title = _split_glued_title(token)
        if title is None:
            chunk.append(token)
            continue
        if leftover:
            chunk.append(leftover)
        if not chunk:
            return None
        people.append(_chunk_to_person(chunk, title))
        chunk = []

    if chunk:
        people.append(_chunk_to_person(chunk, None))

    if len(people) != effective_party_count:
        return None

    return people


def parse_name_element(line: str) -> NameElement:
    """Parse ONE name group. For a body line, use parse_name_line()
    instead -- REQ03 p.10 allows several groups on a single line."""
    stripped = line.strip()

    m = _LEADING_DIGITS_RE.match(stripped)
    if not m:
        raise ElementParseError(
            f"NAME group must start with 1-3 digit number in party: {line!r}"
        )
    number_in_party = int(m.group(1))
    rest = m.group(2)

    if not rest:
        raise ElementParseError(
            f"NAME group has a number in party but nothing after it: {line!r}"
        )

    if "/" not in rest:
        return NameElement(
            raw=stripped,
            number_in_party=number_in_party,
            surname=rest,
            people=[],
            is_group_placeholder=True,
            seat_modifiers=[],
            uses_distinct_surnames=False,
        )

    parts = rest.split("/")
    surname, trailing = parts[0], parts[1:]

    if not surname:
        raise ElementParseError(f"NAME group missing surname before '/': {line!r}")
    if not trailing:
        raise ElementParseError(
            f"NAME group has '/' but no given-name/title tokens after it: {line!r}"
        )

    seat_modifiers: list[str] = []
    if trailing and trailing[-1] in _SEAT_MODIFIER_KEYWORDS:
        seat_modifiers.append(trailing.pop())

    effective_party_count = number_in_party - len(seat_modifiers)
    if effective_party_count < 1:
        raise ElementParseError(
            f"NAME group has more seat-modifier tokens ({seat_modifiers}) "
            f"than number_in_party={number_in_party} can account for: {line!r}"
        )
    if not trailing:
        raise ElementParseError(
            f"NAME group has a seat modifier ({seat_modifiers}) but no "
            f"given-name/title tokens before it: {line!r}"
        )

    known_titles = set(loader.name_title_codes().keys())

    people = _try_parse_shared_surname(trailing, effective_party_count, known_titles)
    uses_distinct_surnames = False

    if people is None:
        full_sequence = [surname] + trailing
        people = _try_parse_distinct_surnames(full_sequence, effective_party_count)
        uses_distinct_surnames = people is not None

    if people is None:
        raise ElementParseError(
            f"NAME group has {len(trailing)} given-name/title tokens after "
            f"the surname (after removing any seat modifier), but the "
            f"effective party count is {effective_party_count} -- this "
            f"doesn't fit the shared-surname grammar ({effective_party_count} "
            f"or {effective_party_count + 1} tokens) or the "
            f"distinct-surnames grammar. Refusing to guess: {line!r}"
        )

    return NameElement(
        raw=stripped,
        number_in_party=number_in_party,
        surname=surname,
        people=people,
        is_group_placeholder=False,
        seat_modifiers=seat_modifiers,
        uses_distinct_surnames=uses_distinct_surnames,
    )


def parse_name_line(line: str) -> list[NameElement]:
    """REQ03 p.10: one NAME line may carry several space-separated name
    groups, e.g. '1AAAAA/AMR 1BBBBB/BMR'. Each group must begin with its
    own number in party."""
    stripped = line.strip()
    if not stripped:
        raise ElementParseError("NAME line is empty")

    groups = stripped.split()
    for i, group in enumerate(groups):
        if not _LEADING_DIGITS_RE.match(group) or group.rstrip("0123456789") == "":
            raise ElementParseError(
                f"NAME line token {i + 1} of {len(groups)} ({group!r}) does "
                f"not begin a name group -- every space-separated group on "
                f"a NAME line must start with its own 1-3 digit number in "
                f"party, immediately followed by the name: {line!r}"
            )

    return [parse_name_element(g) for g in groups]


def parse_name_reference(token: str) -> NameReference:
    stripped = token.strip()

    m = _OPTIONAL_LEADING_DIGITS_RE.match(stripped)
    leading_number = int(m.group(1)) if m.group(1) else None
    rest = m.group(2)

    if not rest or "/" not in rest:
        raise ElementParseError(
            f"Name reference malformed, expected '[N]SURNAME/GIVEN[/TITLE]': {token!r}"
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
                f"Name reference has 2 tokens after the surname, which only "
                f"fits the grammar if the second is a standalone title -- "
                f"got {title!r} in {token!r}"
            )
    else:
        raise ElementParseError(
            f"Name reference has {len(trailing)} tokens after the surname: {token!r}"
        )

    return NameReference(
        raw=stripped,
        leading_number=leading_number,
        surname=surname,
        given_name=given_name,
        title=title,
    )


def render_name_element(name: NameElement) -> str:
    if name.is_group_placeholder:
        return f"{name.number_in_party}{name.surname}"

    if name.uses_distinct_surnames:
        chunks = []
        for person in name.people:
            piece = person.surname or ""
            if person.given_name:
                piece = f"{piece}/{person.given_name}"
            if person.title:
                piece = f"{piece}/{person.title}"
            chunks.append(piece)
        return f"{name.number_in_party}{'/'.join(chunks)}"

    tokens = []
    for person in name.people:
        given = person.given_name or ""
        tokens.append(f"{given}{person.title}" if person.title else given)
    for modifier in name.seat_modifiers:
        tokens.append(modifier)
    return f"{name.number_in_party}{name.surname}/{'/'.join(tokens)}"