from __future__ import annotations

from typing import Union

from typeb.model.elements import (
    DobElement,
    EmailContactElement,
    NameElement,
    OsiPassengerTypeFlagElement,
    SsrChildOrInfantFlagElement,
    SsrFoidElement,
    SsrTicketNumberElement,
)
from typeb.model.passenger import BookingPassenger

ContactElement = Union[
    SsrFoidElement,
    SsrChildOrInfantFlagElement,
    EmailContactElement,
    DobElement,
    OsiPassengerTypeFlagElement,
    SsrTicketNumberElement,
]

PassengerKey = tuple


class CrossReferenceError(Exception):
    pass


def _passenger_key(surname, given_name, title) -> PassengerKey:
    return (surname, given_name, title)


def cross_reference_passengers(
    name_elements: list[NameElement],
    contact_elements: list[ContactElement],
) -> list[BookingPassenger]:
    pool: dict[PassengerKey, dict] = {}
    order: list[PassengerKey] = []

    for ne in name_elements:
        if ne.is_group_placeholder:
            continue
        for person in ne.people:
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
                "ticket_numbers": [],
            }
            order.append(key)

    for element in contact_elements:
        name_ref = getattr(element, "name", None)
        if name_ref is None:
            continue

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

    elif isinstance(element, SsrTicketNumberElement):
        # One TKNE per passenger per segment (REQ03 section 18), so a
        # passenger legitimately accumulates several.
        record["ticket_numbers"].append(element.ticket_number_raw)

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