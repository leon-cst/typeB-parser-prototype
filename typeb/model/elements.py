"""
Domain models for the element layer.

Four element shapes for current scope (AVN, RVR, booking):
  - NameElement            (booking)
  - SegmentElement         (booking) -- glued flight/class/date, per
                            REQ03 p.9-10
  - AvailabilityLine       (AVN body) -- SPACED flight/class/date, per
                            REQ02 p.7-8
  - RecapRequestLine       (RVR body) -- '/'-delimited, per REQ03 p.13

Note AvailabilityLine and SegmentElement are genuinely different shapes,
not two names for the same thing: booking SEGMENT lines glue airline +
flight number + RBD + date into one token ("8G083F24SEP"), while AVN
lines space them out ("AA800 F 01JUN"). This isn't an inconsistency to
resolve -- it's the same "bilateral agreement" formatting variation
flagged throughout REQ02/REQ03, just landing differently across two
different message families that happen to both be in scope right now.

All frozen, like the envelope models -- construct a new one rather than
mutating in place.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Person(BaseModel):
    """One individual within a NAME element's party. REQ03 section 9's
    "3FORD/E/B/C" example is a shared-surname group: one Person per
    given-name token, all sharing the group's surname. Only the LAST
    person in the party can carry a title -- that's the only slot the
    format provides (see typeb.elements.name's docstring for the full
    derivation)."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    given_name: str | None  # None when a title occupies this person's
    # only slot and there's no name left (e.g. "1DUVALIER/MISS" -- no
    # first/middle name was given at all, per REQ03 section 9)
    title: str | None


class NameElement(BaseModel):
    """REQ03 section 9 "Name Element" (p.9-10): '<number in party>
    <surname>/<given name tokens...>', where the LAST given-name token
    may have a title glued onto it (e.g. "JEANMR"), and/or a further
    standalone title token may follow (e.g. ".../EDWARDCHARLES/MR").

    Also covers the group-placeholder shape ("6SEAMEN" -- a group booking
    before individual passenger names are known): no '/' at all, no
    people, just a number and a group name.

    seat_modifiers holds EXST (extra seat, e.g. for an oversized
    passenger) and/or CBBG (cabin baggage occupying its own seat) --
    REQ03 p.11: "Mr. Albert Dooley need Extra seat" -> "2DOOLEY/ALBERTMR
    /EXST". The "2" here is NOT two people -- it's one real person
    (Dooley) plus one "phantom seat" for the extra seat itself, which is
    why this needed its own handling in the parser rather than being
    treated as a second person's given name. Only verified for a single
    modifier attached to one person on a solo NAME line; a group line
    with a modifier on a specific member isn't evidenced by any example
    seen so far.
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    number_in_party: int
    surname: str  # also holds the group name for placeholder lines
    people: list[Person]  # empty for group-placeholder lines
    is_group_placeholder: bool
    seat_modifiers: list[str]  # "EXST" and/or "CBBG", usually empty


class SegmentElement(BaseModel):
    """REQ03 p.9-10 booking-context flight segment:
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


class AvailabilityLine(BaseModel):
    """REQ02 p.7-8 AVN body line, SPACED fields:
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
    """RVR request line, date-range shape -- REQ02 p.13 (not REQ03;
    corrected attribution -- RVR has no worked examples in REQ03 at
    all, only a one-line mention in the identifier table):
    '<airline><flight>/<start date>-<end date>/<frequency>' e.g.
    "8G407/16JUN26-30DEC26/1234567".

    The doc explains the third field directly below its own example:
    "1234567 adalah day operate" -- day-of-week operating pattern
    (1=Monday per the note). Kept as a raw digit string rather than
    parsed further -- the doc doesn't specify an exact length constraint
    (the one example happens to show all 7 days), so frequency_raw isn't
    assumed to always be 7 characters.
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    flight_number: str
    date_range_raw: str  # "16JUN26-30DEC26"
    frequency_raw: str  # "1234567" (day-of-week digits, length not fixed by the doc)


class RecapSingleDateLine(BaseModel):
    """RVR request line, single-date shape -- REQ02 p.14, confirmed by
    two concrete (non-placeholder) worked examples in one real message:
    '<airline><flight>/<date> <citypair>' e.g. "8G123/16JUN26 CGKSIN".

    The route may be omitted entirely -- REQ02 p.13: "Route tidak perlu
    di isi (berarti all)" (route doesn't need to be filled in, meaning:
    all routes). `route` is the literal string "ALL" in that case,
    rather than raising -- this is documented, expected behavior, not a
    malformed line. A separate REQ02 example (p.13) shows a schematic
    placeholder ("BPTOPT") in this position rather than a concrete
    value, which is consistent with this reading but isn't itself a
    literal transmittable example.
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    flight_number: str
    date_raw: str  # "16JUN26"
    route: str  # 6-char city pair, or "ALL" when omitted


class NameReference(BaseModel):
    """A reference to a single already-declared passenger, as embedded
    within an SSR or OSI line (e.g. the trailing
    "-2KUSUMA/BUDISANTOSO/MR" in an SSR FOID line). Distinct from
    NameElement/Person: a NAME line describes an entire party, but a
    name-reference always points at exactly one individual -- even
    though its leading digit (when present) does NOT reflect that; it
    appears to carry over the referenced person's own original party
    size from their NAME line rather than counting anything about this
    reference. REQ03's own formal SSR field table (p.21) shows this
    reference with no leading digit at all ("-RED/PITE"), while a worked
    example directly above it includes one ("-1RED/PETER") -- another
    documented inconsistency. leading_number is kept as an optional raw
    field precisely because of this, not treated as a real count."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    leading_number: int | None
    surname: str
    given_name: str | None
    title: str | None


class SsrFoidElement(BaseModel):
    """Non-automated SSR format (REQ03 p.21's official field table,
    confirmed against a real message): 'SSR FOID <airline>
    <action><count>/<structured text>-<name>' -- e.g.
    "SSR FOID 8G HK1/8472910483756291-2KUSUMA/BUDISANTOSO/MR" carries a
    passport/ID number for a passenger, linked by name."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    action_code: str
    number_in_party: int
    structured_text: str  # the ID/passport number itself
    name: NameReference | None


class SsrChildOrInfantFlagElement(BaseModel):
    """SSR INFT / SSR CHLD. REQ03 section 9 mentions these codes exist
    but never gives a worked format example -- a real gap in the source
    document. Built directly against a real message's shape instead:
    'SSR <code> <airline> <name>', with no action code or segment
    reference at all -- simpler than either official SSR format, not a
    variant of them."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    ssr_code: str  # "INFT" or "CHLD"
    airline_code: str
    name: NameReference


class EmailContactElement(BaseModel):
    """Email contact info: '<SSR|OSI> <airline> <name> E/<email>'. This
    shape is carried by BOTH element identifiers -- e.g.
    "OSI GA 1BAMBANG/MR E/BABANG@GMAIL.COM" (REQ03 p.23) and
    "SSR 8G 1ANGGARA/BAYIBUDI/MR E/BAYI1@GMAIL.COM" (a real message,
    no 4-letter SSR code at all). Per REQ03 p.18, SSR vs OSI marks
    whether the sender expects an acknowledgement (SSR) or is just
    informing (OSI) -- `source` preserves that distinction rather than
    collapsing both into one identical shape and losing it."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    source: str  # "SSR" or "OSI"
    airline_code: str
    name: NameReference
    email: str


class DobElement(BaseModel):
    """Date-of-birth info: '<SSR|OSI> <airline> <name> DOB/<date>'.
    Same SSR/OSI duality as EmailContactElement -- see its docstring.
    date_of_birth_raw is kept as-is rather than normalized -- REQ03's own
    worked example uses a 4-digit year ("DOB/03JUL2026") while real
    traffic seen so far uses 2-digit ("DOB/10MAY85"); not guessing which
    convention a given sender means."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    source: str  # "SSR" or "OSI"
    airline_code: str
    name: NameReference
    date_of_birth_raw: str


class OsiPassengerTypeFlagElement(BaseModel):
    """OSI CHD / OSI INF passenger-type flag (REQ03 p.22 official
    examples: "OSI YY 1 CHD 1MARSH/E", "OSI YY 1 INF 1POPIV/O").
    `unexplained_field` is the literal "1" that appears between the
    airline code and CHD/INF in every example seen so far (spec's own
    and real traffic) -- its meaning isn't explained anywhere in the
    source document, so it's kept as an opaque raw field rather than
    interpreted or named as if its purpose were known."""
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    raw: str
    airline_code: str
    unexplained_field: str
    passenger_type: str  # "CHD" or "INF"
    name: NameReference