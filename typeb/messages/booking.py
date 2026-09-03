from __future__ import annotations

from typeb.elements.cross_reference import cross_reference_passengers, validate_party_size
from typeb.elements.errors import ElementParseError
from typeb.envelope.parser import parse_envelope
from typeb.messages._shared_body import parse_shared_body
from typeb.model.booking import BookingMessage, GroupPlaceholder
from typeb.model.elements import (
    AutomatedSsrElement,
    OsiContactAddressElement,
    OsiPartyCountElement,
    OsiRecordLocatorElement,
    SegmentElement,
    SsrGroupElement,
    SsrGroupFareElement,
    SsrGroupSeatElement,
    SsrRecordLocatorElement,
)


def parse_booking_message(raw: str) -> BookingMessage:
    envelope, body_lines, warnings = parse_envelope(raw)

    if envelope.effective_identifier != "BOOKING":
        raise ElementParseError(
            f"parse_booking_message called on a non-booking message "
            f"(identifier={envelope.effective_identifier!r})."
        )

    body = parse_shared_body(body_lines, warnings)

    # No reliable wire-level signal distinguishes ARRIVAL from SEGMENT
    # lines, so this stays empty until a real signal is found.
    arrival_elements: list[SegmentElement] = []

    passengers = cross_reference_passengers(
        body.current_name_elements, body.contact_elements, body.name_changes
    )

    grps_by_group_name: dict[str, int] = {}
    for e in body.contact_elements:
        if not isinstance(e, SsrGroupElement) or not e.group_name:
            continue
        digits = "".join(c for c in e.structured_text if c.isdigit())
        if digits:
            grps_by_group_name[e.group_name] = int(digits)

    group_placeholders = []
    for ne in body.current_name_elements:
        if not ne.is_group_placeholder:
            continue
        group_name = ne.surname + (
            f"/{ne.group_name_suffix}" if ne.group_name_suffix else ""
        )
        group_placeholders.append(
            GroupPlaceholder(
                surname=ne.surname,
                number_in_party=ne.number_in_party,
                group_name_suffix=ne.group_name_suffix,
                confirmed_party_size=grps_by_group_name.get(group_name),
            )
        )

    airline_record_locators = [
        e.record_locator
        for e in body.contact_elements
        if isinstance(e, (SsrRecordLocatorElement, OsiRecordLocatorElement))
    ]
    group_fare_info = [e for e in body.contact_elements if isinstance(e, SsrGroupFareElement)]
    group_seat_requests = [e for e in body.contact_elements if isinstance(e, SsrGroupSeatElement)]
    contact_addresses = [e for e in body.contact_elements if isinstance(e, OsiContactAddressElement)]
    party_count_notices = [e for e in body.contact_elements if isinstance(e, OsiPartyCountElement)]
    automated_ssrs = [e for e in body.contact_elements if isinstance(e, AutomatedSsrElement)]

    for segment in body.segments:
        validate_party_size(body.current_name_elements, segment.number_in_party)

    return BookingMessage(
        envelope=envelope,
        passengers=passengers,
        name_elements=body.name_elements,
        name_changes=body.name_changes,
        group_placeholders=group_placeholders,
        arrival_elements=arrival_elements,
        segments=body.segments,
        airline_record_locators=airline_record_locators,
        group_fare_info=group_fare_info,
        group_seat_requests=group_seat_requests,
        contact_addresses=contact_addresses,
        party_count_notices=party_count_notices,
        automated_ssrs=automated_ssrs,
        warnings=body.warnings,
        unrecognized_lines=body.unrecognized_lines,
    )