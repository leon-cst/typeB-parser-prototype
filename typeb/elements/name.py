from __future__ import annotations

import re

from typeb.elements.errors import ElementParseError
from typeb.model.elements import NameChange, NameElement, NameReference, Person
from typeb.tables import loader

_LEADING_DIGITS_RE = re.compile(r"^(\d{1,3})(.*)$")
_OPTIONAL_LEADING_DIGITS_RE = re.compile(r"^(\d{1,3})?(.*)$")
_SEAT_MODIFIER_KEYWORDS = {"EXST", "CBBG"}
_CHNT_MARKER = "CHNT"  # sentinel used by split_name_change_boundary()
EXCLUDED_NAME_LINE_MARKER = "\0EXCLUDED_NAME_LINE\0"  # sentinel a caller
# (typeb.messages.booking) substitutes for a NAME-kind line it excluded
# for exceeding the 69-character limit -- lets split_name_change_boundary
# report "a NAME line was here but excluded" instead of a misleading
# "no NAME line here at all".


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
        if number_in_party < 9: # MINIMUM GROUP PARTY NUMBER 
            raise ElementParseError(
                f"NAME group with no '/' and number_in_party={number_in_party} "
                f"< 9 requires a title -- only 9 or more is treated as a "
                f"group placeholder: {line!r}"
            )
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

    if people is None and len(trailing) == 1 and trailing[0] not in known_titles:
        # REQ03 section 16: a group/tour name substitutes for all
        # individual names, e.g. "30SITA/TOUR". Only reached once both
        # individual-name grammars have already failed to match, and
        # only for a single trailing token that isn't a known title --
        # so this doesn't compete with or shadow either of them.
        if number_in_party < 9:
            raise ElementParseError(
                f"NAME group/tour placeholder with number_in_party="
                f"{number_in_party} < 9 requires a title -- only 9 or "
                f"more is treated as a group placeholder: {line!r}"
            )
        return NameElement(
            raw=stripped,
            number_in_party=number_in_party,
            surname=surname,
            people=[],
            is_group_placeholder=True,
            group_name_suffix=trailing[0],
            seat_modifiers=seat_modifiers,
            uses_distinct_surnames=False,
        )

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


def _align_name_changes(
    before: list[NameElement], after: list[NameElement], raw_before: str, raw_after: str
) -> list[NameChange]:

    before_counts: dict[str, int] = {}
    after_counts: dict[str, int] = {}
    for b in before:
        before_counts[b.raw] = before_counts.get(b.raw, 0) + 1
    for a in after:
        after_counts[a.raw] = after_counts.get(a.raw, 0) + 1

    anchors: list[tuple[int, int]] = []  # (before_index, after_index)
    after_index_by_raw: dict[str, int] = {}
    for j, a in enumerate(after):
        if a.raw not in after_index_by_raw:
            after_index_by_raw[a.raw] = j

    last_after_index = -1
    for i, b in enumerate(before):
        if before_counts.get(b.raw) != 1 or after_counts.get(b.raw) != 1:
            continue
        j = after_index_by_raw.get(b.raw)
        if j is None or j <= last_after_index:
            continue
        anchors.append((i, j))
        last_after_index = j

    changes: list[NameChange] = []
    prev_i, prev_j = -1, -1
    boundaries = anchors + [(len(before), len(after))]
    for i, j in boundaries:
        old_gap = before[prev_i + 1:i]
        new_gap = after[prev_j + 1:j]
        if old_gap or new_gap:
            if not old_gap or not new_gap:
                raise ElementParseError(
                    f"Passenger list rewrite after CHNT doesn't align: "
                    f"{len(old_gap)} unmatched entr{'y' if len(old_gap) == 1 else 'ies'} "
                    f"before CHNT vs {len(new_gap)} after, with no way to "
                    f"pair them. Before: {raw_before!r}. After: {raw_after!r}"
                )
            if len(old_gap) == len(new_gap):
                for old_entry, new_entry in zip(old_gap, new_gap):
                    changes.append(
                        NameChange(
                            raw=f"{old_entry.raw} -> {new_entry.raw}",
                            old=[old_entry],
                            new=[new_entry],
                        )
                    )
            elif len(old_gap) == 1:
                old_total = old_gap[0].number_in_party
                new_total = sum(n.number_in_party for n in new_gap)
                if old_total != new_total:
                    raise ElementParseError(
                        f"CHNT change for {old_gap[0].raw!r} declares "
                        f"{old_total} pax before but {new_total} after -- "
                        f"a split must preserve the total number in party."
                    )
                changes.append(
                    NameChange(
                        raw=f"{old_gap[0].raw} -> {' '.join(n.raw for n in new_gap)}",
                        old=old_gap,
                        new=new_gap,
                    )
                )
            else:
                raise ElementParseError(
                    f"CHNT change has {len(old_gap)} unmatched entries "
                    f"before CHNT mapping to {len(new_gap)} after -- only "
                    f"a single entry splitting into multiple, or equal "
                    f"counts on both sides, is supported -- not merging "
                    f"or reshuffling a different number of entries at "
                    f"once. Before: {[e.raw for e in old_gap]}, after: "
                    f"{[e.raw for e in new_gap]}"
                )
        prev_i, prev_j = i, j

    return changes


def split_name_change_boundary(
    name_lines: list[str],
) -> tuple[list[NameElement], list[NameChange]]:
    if _CHNT_MARKER not in name_lines:
        return [
            g for line in name_lines
            if line != EXCLUDED_NAME_LINE_MARKER
            for g in parse_name_line(line)
        ], []

    if name_lines.count(_CHNT_MARKER) > 1:
        raise ElementParseError(
            "Message has more than one CHNT line -- only one name-change "
            "boundary is supported."
        )

    boundary = name_lines.index(_CHNT_MARKER)
    before_lines, after_lines = name_lines[:boundary], name_lines[boundary + 1:]

    before_excluded = before_lines.count(EXCLUDED_NAME_LINE_MARKER)
    after_excluded = after_lines.count(EXCLUDED_NAME_LINE_MARKER)
    before_usable = [l for l in before_lines if l != EXCLUDED_NAME_LINE_MARKER]
    after_usable = [l for l in after_lines if l != EXCLUDED_NAME_LINE_MARKER]

    if not before_usable:
        reason = (
            f"a NAME line was there but excluded for exceeding the "
            f"69-character limit (see warnings)"
            if before_excluded else "REQ03 section 25/30 requires the "
            "full passenger list to precede CHNT"
        )
        raise ElementParseError(f"CHNT appeared with no usable NAME line before it -- {reason}.")
    if not after_usable:
        reason = (
            f"a NAME line was there but excluded for exceeding the "
            f"69-character limit (see warnings)"
            if after_excluded else "REQ03 section 25/30 requires the "
            "full, rewritten passenger list to follow CHNT"
        )
        raise ElementParseError(f"CHNT appeared with no usable NAME line after it -- {reason}.")

    passengers = [g for line in before_usable for g in parse_name_line(line)]
    after_passengers = [g for line in after_usable for g in parse_name_line(line)]

    name_changes = _align_name_changes(
        passengers, after_passengers, " ".join(before_usable), " ".join(after_usable)
    )

    return passengers, name_changes


def apply_name_changes(
    passengers: list[NameElement], name_changes: list[NameChange]
) -> list[NameElement]:
    """Returns the post-CHNT passenger list: each changed entry
    replaced by its new name(s) (a split contributes multiple entries
    in place of the one it replaces); unaffected passengers unchanged.
    Used for cross-referencing and party-size validation, which need
    the current state -- the full pre-CHNT list stays on
    BookingMessage.name_elements for audit."""
    if not name_changes:
        return passengers

    old_raw_to_new: dict[str, list[NameElement]] = {}
    for change in name_changes:
        for old_entry in change.old:
            old_raw_to_new[old_entry.raw] = change.new

    result: list[NameElement] = []
    consumed_multi_old_raws: set[str] = set()
    for p in passengers:
        if p.raw in old_raw_to_new:
            if p.raw in consumed_multi_old_raws:
                continue
            result.extend(old_raw_to_new[p.raw])
            consumed_multi_old_raws.add(p.raw)
        else:
            result.append(p)
    return result


def parse_name_reference(token: str) -> NameReference:
    stripped = token.strip()

    m = _OPTIONAL_LEADING_DIGITS_RE.match(stripped)
    leading_number = int(m.group(1)) if m.group(1) else None
    rest = m.group(2)

    if not rest:
        raise ElementParseError(f"Name reference missing a name: {token!r}")

    if "/" not in rest:
        given_name, title = _split_glued_title(rest)
        if title is not None:
            # given name + title suffix, no surname of its own -- an
            # infant/child referenced via the adult's shared-surname
            # NAME group (e.g. "1BAYIBUDIINF"). cross_reference_passengers
            # matches this on (given_name, title) alone.
            return NameReference(
                raw=stripped,
                leading_number=leading_number,
                surname=None,
                given_name=given_name,
                title=title,
            )
        # Bare surname, no given name/title (REQ03 section 25: "OSI YY
        # TCP3 1ALLEN") -- same no-slash grammar NameElement already
        # accepts for a group placeholder, here for a single reference.
        return NameReference(
            raw=stripped,
            leading_number=leading_number,
            surname=rest,
            given_name=None,
            title=None,
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
        if name.group_name_suffix:
            return f"{name.number_in_party}{name.surname}/{name.group_name_suffix}"
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