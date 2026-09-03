from __future__ import annotations

from typeb.elements.cross_reference import cross_reference_passengers, validate_party_size
from typeb.elements.errors import ElementParseError
from typeb.envelope.parser import parse_envelope
from typeb.messages._shared_body import parse_shared_body
from typeb.model.dvd import DvdMessage
from typeb.model.elements import (
    AutomatedSsrElement,
    OsiOriginalLocatorElement,
    OsiPartyCountElement,
    OsiRecordLocatorElement,
    SsrRecordLocatorElement,
)


def parse_dvd_message(raw: str) -> DvdMessage:
    envelope, body_lines, warnings = parse_envelope(raw)

    if envelope.effective_identifier != "DVD":
        raise ElementParseError(
            f"parse_dvd_message called on a non-DVD message "
            f"(identifier={envelope.effective_identifier!r})."
        )

    body = parse_shared_body(body_lines, warnings, allow_malformed_segments=True)

    passengers = cross_reference_passengers(
        body.current_name_elements, body.contact_elements, body.name_changes
    )

    original_locators = [
        e for e in body.contact_elements if isinstance(e, OsiOriginalLocatorElement)
    ]

    record_locator_recovered_from_osi = False
    if not envelope.record_locators and original_locators:
        record_locator_recovered_from_osi = True

    airline_record_locators = [
        e.record_locator
        for e in body.contact_elements
        if isinstance(e, (SsrRecordLocatorElement, OsiRecordLocatorElement))
    ]
    if record_locator_recovered_from_osi:
        airline_record_locators = [
            *airline_record_locators,
            *(loc.glued_locator for loc in original_locators),
        ]

    automated_ssrs = [e for e in body.contact_elements if isinstance(e, AutomatedSsrElement)]
    party_count_notices = [e for e in body.contact_elements if isinstance(e, OsiPartyCountElement)]

    for segment in body.segments:
        validate_party_size(body.current_name_elements, segment.number_in_party)

    return DvdMessage(
        envelope=envelope,
        airline_record_locators=airline_record_locators,
        automated_ssrs=automated_ssrs,
        party_count_notices=party_count_notices,
        passengers=passengers,
        name_elements=body.name_elements,
        name_changes=body.name_changes,
        segments=body.segments,
        original_locators=original_locators,
        record_locator_recovered_from_osi=record_locator_recovered_from_osi,
        warnings=body.warnings,
        unrecognized_lines=body.unrecognized_lines,
    )