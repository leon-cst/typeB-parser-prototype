from __future__ import annotations

from typing import Union

from typeb.model.elements import (
    AutomatedSsrElement,
    DobElement,
    EmailContactElement,
    NameElement,
    OsiPassengerTypeFlagElement,
    SsrChildOrInfantFlagElement,
    SsrFoidElement,
    SsrTicketNumberElement,
)
from typeb.model.passenger import BookingPassenger, TicketNumberRecord

ContactElement = Union[
    SsrFoidElement,
    SsrChildOrInfantFlagElement,
    EmailContactElement,
    DobElement,
    OsiPassengerTypeFlagElement,
    SsrTicketNumberElement,
    AutomatedSsrElement,
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
                    f"Two different NAME elements resolve to the same "
                    f"(surname, given_name, title) key {key} -- can't "
                    f"disambiguate which one any later OSI/SSR reference "
                    f"to this name means. NAME line: {ne.raw!r}. If this "
                    f"name is legitimately declared only once in the "
                    f"real message, check whether an adjacent SSR/OSI "
                    f"line was split across two physical lines (REQ03's "
                    f"line-continuation convention, e.g. a trailing '-' "
                    f"or repeated code+airline prefix) -- line "
                    f"continuation isn't parsed yet, so a continued line "
                    f"can be misread as a second, duplicate NAME element."
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
                "_ticket_number_groups": {},  # ticket_number -> {"airline_code": str, "segments": [...]}
            }
            order.append(key)

    for element in contact_elements:
        if isinstance(element, AutomatedSsrElement):
            # VGML/SMSW/etc. may reference a passenger who is being
            # cancelled or replaced in this same message (e.g. a name
            # change dropping a special-service request tied to the
            # old name) -- not an error, and not this layer's job to
            # resolve. Captured by the caller via contact_elements;
            # nothing to attach to a BookingPassenger record.
            continue

        name_ref = getattr(element, "name", None)
        if name_ref is None:
            continue
        if isinstance(name_ref, NameElement):
            # A multi-person shared-surname reference (REQ03 section 16
            # group SSRs, e.g. "-5ARDMORE/BOB/SUE/TIM/TOM/TONY") refers
            # to several passengers at once, not one -- there's no
            # single BookingPassenger record to attach this to, so it's
            # left out of cross-referencing rather than guessing which
            # one person it means.
            continue

        if name_ref.surname is None:
            candidates = [
                k for k in pool
                if k[1] == name_ref.given_name and k[2] == name_ref.title
            ]
            if len(candidates) == 1:
                key = candidates[0]
            elif not candidates:
                raise CrossReferenceError(
                    f"{type(element).__name__} references a passenger not "
                    f"found in any NAME element: given_name="
                    f"{name_ref.given_name!r}, title={name_ref.title!r} "
                    f"(from line: {element.raw!r})"
                )
            else:
                raise CrossReferenceError(
                    f"{type(element).__name__} references "
                    f"given_name={name_ref.given_name!r}, "
                    f"title={name_ref.title!r} without a surname, and "
                    f"{len(candidates)} different NAME elements match -- "
                    f"can't tell which one this means (from line: "
                    f"{element.raw!r})"
                )
        else:
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

    return [_finalize_passenger(pool[key]) for key in order]


def _finalize_passenger(record: dict) -> BookingPassenger:
    ticket_groups = record.pop("_ticket_number_groups")
    record["ticket_numbers"] = [
        TicketNumberRecord(
            ticket_number=ticket_number,
            airline_code=group["airline_code"],
            segments=group["segments"],
        )
        for ticket_number, group in ticket_groups.items()
    ]
    return BookingPassenger(**record)


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
        groups = record["_ticket_number_groups"]
        group = groups.setdefault(
            element.ticket_number_raw,
            {"airline_code": element.airline_code, "segments": []},
        )
        if group["airline_code"] != element.airline_code:
            raise CrossReferenceError(
                f"Ticket number {element.ticket_number_raw!r} was "
                f"already reported under airline "
                f"{group['airline_code']!r}, but this line reports it "
                f"under {element.airline_code!r} -- can't represent one "
                f"ticket under two airlines. Line: {element.raw!r}"
            )
        group["segments"].append(element.segment_reference_raw)

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
    total_name_party = sum(ne.number_in_party for ne in name_elements)
    if total_name_party != segment_number_in_party:
        return [
            f"NAME elements declare a total party size of "
            f"{total_name_party}, but the segment requests "
            f"{segment_number_in_party} seat(s). This can be legitimate "
            f"(REQ03 p.11: infant inclusion in number_in_party is "
            f"bilateral-agreement-dependent) but is worth a human check."
        ]
    return []