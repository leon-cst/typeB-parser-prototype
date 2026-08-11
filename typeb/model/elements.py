"""
Domain models for the element layer.

"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Person(BaseModel):
    """One individual within a NAME element's party. Surname is None by default"""

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    surname: str | None = None  # only set for the distinct-surnames shape
    given_name: str | None  # None when a title occupies this person's
    # only slot and there's no name left (e.g. "1DUVALIER/MISS" -- no
    # first/middle name was given at all, per REQ03 section 9)
    title: str | None


class NameElement(BaseModel):
    """REQ03 section 9 "Name Element" """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    number_in_party: int
    surname: str  # also holds the group name for placeholder lines
    people: list[Person]  # empty for group-placeholder lines
    is_group_placeholder: bool
    group_name_suffix: str | None = None  # e.g. "TOUR" in "30SITA/TOUR" --
    # only set for the slash-form group placeholder, None for the
    # no-slash form (e.g. "6SEAMEN") and for ordinary NAME elements
    seat_modifiers: list[str]  # "EXST" and/or "CBBG", usually empty
    uses_distinct_surnames: bool  # see docstring above


class SegmentElement(BaseModel):
    """booking-context flight segment:
    '<airline><flight><rbd><date> <board><off> <action><count> [<dep> <arr>]'
    with the first field glued, e.g. "8G083F24SEP CGKDPS NN1 0910 1015"."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    flight_number: str
    reservation_booking_designator: str  # RBD / class of service
    date_raw: str  # ddMMM, no year -- REQ02/REQ03 note year presence is
    # bilateral-agreement-dependent; kept raw rather than guessing
    board_point: str
    off_point: str
    action_code: str  # cross-reference typeb.tables.loader.segment_status_codes()
    number_in_party: int
    departure_time_raw: str | None
    arrival_time_raw: str | None
    arrival_day_offset: int | None = None


class AvailabilityLine(BaseModel):
    """AVN body line, SPACED fields:
    '<airline><flight> <rbd> <date> <board><off>' e.g. "AA800 F 01JUN CGKDPS"."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    flight_number: str
    reservation_booking_designator: str
    date_raw: str
    board_point: str
    off_point: str


class RecapDateRangeLine(BaseModel):
    """RVR request line, date-range shape """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    flight_number: str
    date_range_raw: str  # "16JUN26-30DEC26"
    frequency_raw: str  # "1234567" (day-of-week digits, length not fixed by the doc)


class RecapSingleDateLine(BaseModel):
    """RVR request line, single-date shape """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    flight_number: str
    date_raw: str  # "16JUN26"
    route: str  # 6-char city pair, or "ALL" when omitted


class NameReference(BaseModel):
    """A reference to a single already-declared passenger, as embedded
    within an SSR or OSI line. """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    leading_number: int | None
    surname: str
    given_name: str | None
    title: str | None


class SsrFoidElement(BaseModel):

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    action_code: str
    number_in_party: int
    structured_text: str  # the ID/passport number itself
    name: NameReference | None


class SsrChildOrInfantFlagElement(BaseModel):

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    ssr_code: str  # "INFT" or "CHLD"
    airline_code: str
    name: NameReference


class EmailContactElement(BaseModel):

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    source: str  # "SSR" or "OSI"
    airline_code: str
    name: NameReference
    email: str


class DobElement(BaseModel):

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    source: str  # "SSR" or "OSI"
    airline_code: str
    name: NameReference
    date_of_birth_raw: str


class OsiPassengerTypeFlagElement(BaseModel):

    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    unexplained_field: str
    passenger_type: str  # "CHD" or "INF"
    name: NameReference

class SsrTicketNumberElement(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)
 
    raw: str
    airline_code: str
    action_code: str | None
    number_in_party: int | None
    segment_reference_raw: str
    name: NameReference | None
    ticket_number_raw: str
 
 
class SsrRecordLocatorElement(BaseModel):
    """SSR RLOC -- the airline's own PNR code for a passive segment
    (REQ03 section 17)."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)
 
    raw: str
    airline_code: str
    action_code: str | None
    number_in_party: int | None
    segment_reference_raw: str
    name: NameReference | None
    record_locator: str
 
 
class SsrGroupElement(BaseModel):
    """SSR GRPS. REQ03 section 12 states action code and number in party
    are optional for GRPS/MEDA/OTHS."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)
 
    raw: str
    airline_code: str
    structured_text: str
    group_name: str | None
 
 
class OsiRecordLocatorElement(BaseModel):
    """OSI ... RLOC ... -- REQ03 section 17's alternative to SSR RLOC."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)
 
    raw: str
    airline_code: str
    record_locator_airline: str
    record_locator: str


class OsiContactAddressElement(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    action_code: str
    detail: str


class SsrGroupFareElement(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    status_code: str
    detail: str | None


class SsrGroupSeatElement(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    action_code: str
    number_in_party: int
    segment_reference_raw: str


class SsrTicketingTimeLimitElement(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    status_code: str
    city_code: str
    time_raw: str | None
    date_raw: str | None
    removal_note: str | None


class AutomatedSsrElement(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    ssr_code: str
    airline_code: str
    action_code: str | None
    number_in_party: int | None
    segment_reference_raw: str
    name: NameReference | NameElement | None
    free_text: str | None