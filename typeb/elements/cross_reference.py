"""
Generic cross-reference layer: matches OSI/SSR name-references back to
the Person they describe (from a NAME element), and merges every
attribute scattered across multiple lines (email, DOB, FOID, child/
infant status, seat modifiers) into one BookingPassenger per person.

Deliberately generic, not booking-specific: this operates purely on
NameElement/NameReference data, not on anything booking-message-
specific, so any future message type built on the same element
vocabulary (DVD, ASC, TLR, ...) can reuse it directly rather than
needing its own copy.

Matching key: (surname, given_name, title) -- the only thing the wire
format gives us to link a NAME line's Person to an OSI/SSR reference,
since there's no ID number connecting them. This is fragile by
construction (a typo, or a title present on one line and missing on
another, silently breaks the match), so this module raises loudly on
ambiguity rather than guessing, per explicit instruction:
  - two different people resolving to the same (surname, given_name,
    title) key -- can't tell which one a later reference means
  - an OSI/SSR reference that matches no one at all
  - conflicting passenger-type signals for the same person (e.g. one
    line says CHD, another says INF for the same key)
"""
from __future__ import annotations

from typing import Union

from typeb.model.elements import (
    DobElement,
    EmailContactElement,
    NameElement,
    OsiPassengerTypeFlagElement,
    SsrChildOrInfantFlagElement,
    SsrFoidElement,
)
from typeb.model.passenger import BookingPassenger

ContactElement = Union[
    SsrFoidElement,
    SsrChildOrInfantFlagElement,
    EmailContactElement,
    DobElement,
    OsiPassengerTypeFlagElement,
]

PassengerKey = tuple


class CrossReferenceError(Exception):
    """Raised on ambiguous or unmatched name-references. Never silently
    guesses which passenger an element means -- see module docstring."""


def _passenger_key(
    surname: str, given_name: str | None, title: str | None
) -> PassengerKey:
    return (surname, given_name, title)


def cross_reference_passengers(
    name_elements: list[NameElement],
    contact_elements: list[ContactElement],
) -> list[BookingPassenger]:
    """Build one BookingPassenger per real (non-placeholder) person
    declared across `name_elements`, with every matching element in
    `contact_elements` merged in. Order of the returned list follows the
    order people first appear across the NAME elements."""
    pool: dict[PassengerKey, dict] = {}
    order: list[PassengerKey] = []

    for ne in name_elements:
        if ne.is_group_placeholder:
            continue
        for person in ne.people:
            # Person.surname is only set under Logic B (distinct
            # surnames) -- see typeb.model.elements.Person's docstring.
            # Under Logic A (shared surname), it's None, meaning "use
            # the NameElement's own surname" as before.
            person_surname = person.surname if person.surname else ne.surname
            key = _passenger_key(person_surname, person.given_name, person.title)
            if key in pool:
                raise CrossReferenceError(
                    f"Two different people resolve to the same "
                    f"(surname, given_name, title) key {key} -- can't "
                    f"disambiguate which one any later OSI/SSR reference "
                    f"to this name means. NAME line: {ne.raw!r}"
                )
            pool[key] = {
                "surname": person_surname,
                "given_name": person.given_name,
                "title": person.title,
                "passenger_type": "ADT",
                "seat_modifiers": list(ne.seat_modifiers),
                "email": None,
                "date_of_birth_raw": None,
                "foid": None,
            }
            order.append(key)

    for element in contact_elements:
        name_ref = getattr(element, "name", None)
        if name_ref is None:
            continue  # e.g. SSR FOID with no name attached -- nothing to link

        key = _passenger_key(name_ref.surname, name_ref.given_name, name_ref.title)
        record = pool.get(key)
        if record is None:
            raise CrossReferenceError(
                f"{type(element).__name__} references a passenger not "
                f"found in any NAME element: surname={name_ref.surname!r}, "
                f"given_name={name_ref.given_name!r}, "
                f"title={name_ref.title!r} (from line: {element.raw!r})"
            )

        _apply_element(record, element)

    return [BookingPassenger(**pool[key]) for key in order]


def _apply_element(record: dict, element: ContactElement) -> None:
    if isinstance(element, SsrFoidElement):
        record["foid"] = element.structured_text

    elif isinstance(element, SsrChildOrInfantFlagElement):
        new_type = "INF" if element.ssr_code == "INFT" else "CHD"
        _set_passenger_type(record, new_type, element)

    elif isinstance(element, EmailContactElement):
        record["email"] = element.email

    elif isinstance(element, DobElement):
        record["date_of_birth_raw"] = element.date_of_birth_raw

    elif isinstance(element, OsiPassengerTypeFlagElement):
        new_type = "INF" if element.passenger_type == "INF" else "CHD"
        _set_passenger_type(record, new_type, element)

    else:
        raise CrossReferenceError(
            f"Don't know how to apply {type(element).__name__} to a "
            f"passenger record -- add a case in _apply_element."
        )


def _set_passenger_type(record: dict, new_type: str, element: ContactElement) -> None:
    current = record["passenger_type"]
    if current != "ADT" and current != new_type:
        raise CrossReferenceError(
            f"Conflicting passenger-type signals for "
            f"{record['surname']}/{record['given_name']}: already "
            f"determined as {current!r}, but {type(element).__name__} "
            f"says {new_type!r} (from line: {element.raw!r})"
        )
    record["passenger_type"] = new_type


def validate_party_size(
    name_elements: list[NameElement], segment_number_in_party: int
) -> list[str]:
    """Cross-check REQ03's own stated invariant (p.10): total number in
    party across NAME elements should equal the flight segment's seat
    count. Returns warning strings rather than raising -- REQ03 p.11
    says infant-inclusion in number_in_party is bilateral-agreement-
    dependent, so a mismatch can be legitimate, not necessarily an
    error. Surfaces the discrepancy for a human (or later, a
    PartnerProfile) to resolve rather than blocking the parse."""
    total_name_party = sum(
        ne.number_in_party for ne in name_elements if not ne.is_group_placeholder
    )
    if total_name_party != segment_number_in_party:
        return [
            f"NAME elements declare a total party size of "
            f"{total_name_party}, but the segment requests "
            f"{segment_number_in_party} seat(s). This can be legitimate "
            f"(REQ03 p.11: infant inclusion in number_in_party is "
            f"bilateral-agreement-dependent) but is worth a human check."
        ]
    return []