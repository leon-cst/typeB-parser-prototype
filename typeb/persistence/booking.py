"""
Maps a parsed BookingMessage onto the relational schema (Pnr,
Passenger, FlightSegment, Osi, Ssr).

Two-phase by design, matching the project's fail-loud principle:
analyze_booking_message() does a pure, read-only dry run and reports
exactly what would be created and what can't be mapped yet. Nothing
touches the database until save_booking_message() is called with an
already-reviewed analysis, so a message with unmappable content never
gets silently and partially saved.

Deliberately separate from typeb/model/ (parser) and typeb/db/ (ORM) --
this is the one place those two are allowed to know about each other.
"""
from __future__ import annotations
from datetime import time

from dataclasses import dataclass, field

from typeb.db.models import FlightSegment, Osi, Passenger, Pnr, Ssr
from typeb.extensions import db
from typeb.model.booking import BookingMessage
from typeb.model.elements import (
    AutomatedSsrElement,
    DobElement,
    EmailContactElement,
    OsiPassengerTypeFlagElement,
    SsrPassengerTypeFlagElement,
)

def _parse_hhmm(raw: str | None) -> time | None:
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) != 4 or not raw.isdigit():
        raise ValueError(f"Expected 4-digit HHMM time, got {raw!r}")
    hour, minute = int(raw[:2]), int(raw[2:])
    return time(hour=hour, minute=minute)

@dataclass
class PnrPlan:
    pnr_code: str
    booking_office_code: str
    pos_travel_agent_id: str | None
    pos_city_code: str | None
    pos_user_type: str | None


@dataclass
class PassengerPlan:
    index: int  # position in message.passengers, used to link segments/osi/ssr back
    family_name: str
    first_name_middle_name: str | None
    title: str | None
    number_in_party: int | None
    passenger_type: str
    email: str | None
    date_of_birth_raw: str | None
    foid: str | None


@dataclass
class SegmentPlan:
    airline_code: str
    flight_number: str
    rbd_class: str | None
    flight_date_raw: str
    boarding_point: str
    off_point: str
    action_code: str
    number_in_party: int
    departure_time: time | None
    arrival_time: time | None
    arrival_day_offset: int | None


@dataclass
class OsiPlan:
    airline_code: str
    information_text: str
    passenger_index: int | None  # index into passenger_plans, or None


@dataclass
class SsrPlan:
    ssr_code: str
    airline_code: str | None
    action_code: str | None
    free_text: str | None
    passenger_index: int | None


@dataclass
class BookingSavePlan:
    """Result of analyze_booking_message(). Pass this to
    save_booking_message() unchanged to actually write it."""
    pnrs: list[PnrPlan] = field(default_factory=list)
    passengers: list[PassengerPlan] = field(default_factory=list)
    segments: list[SegmentPlan] = field(default_factory=list)
    osi_entries: list[OsiPlan] = field(default_factory=list)
    ssr_entries: list[SsrPlan] = field(default_factory=list)
    unmappable: list[str] = field(default_factory=list)  # human-readable descriptions

    @property
    def has_unmappable(self) -> bool:
        return bool(self.unmappable)


def _find_number_in_party(message: BookingMessage, surname: str, given_name: str | None, title: str | None) -> int | None:
    """Cross-references a flattened passenger back to the NameElement
    group it came from, to recover number_in_party -- see
    BookingPassenger, which has no such field of its own."""
    for ne in message.name_elements:
        for person in ne.people:
            person_surname = person.surname or ne.surname
            if person_surname == surname and person.given_name == given_name and person.title == title:
                return ne.number_in_party
    return None


def _find_passenger_index(passenger_plans: list[PassengerPlan], surname: str | None, given_name: str | None, title: str | None) -> int | None:
    for p in passenger_plans:
        if p.family_name == surname and p.first_name_middle_name == given_name and p.title == title:
            return p.index
    return None


def analyze_booking_message(message: BookingMessage) -> BookingSavePlan:
    """Pure, read-only. Builds the full save plan and lists anything
    that can't be represented yet, without touching the database."""
    plan = BookingSavePlan()

    if not message.envelope.record_locators:
        plan.unmappable.append(
            "No record locator in this message -- cannot create a PNR row."
        )
        return plan

    for rl in message.envelope.record_locators:
        plan.pnrs.append(PnrPlan(
            pnr_code=rl.location_of_record,
            booking_office_code=rl.booking_office,
            pos_travel_agent_id=rl.travel_agent_city_code,
            pos_city_code=rl.city_airport_code,
            pos_user_type=rl.user_type,
        ))

    for i, p in enumerate(message.passengers):
        plan.passengers.append(PassengerPlan(
            index=i,
            family_name=p.surname,
            first_name_middle_name=p.given_name,
            title=p.title,
            number_in_party=_find_number_in_party(message, p.surname, p.given_name, p.title),
            passenger_type=p.passenger_type,
            email=p.email,
            date_of_birth_raw=p.date_of_birth_raw,
            foid=p.foid,
        ))
        if p.seat_modifiers:
            plan.unmappable.append(
                f"{p.surname}/{p.given_name}: seat_modifiers "
                f"{p.seat_modifiers} has no column yet."
            )
        if p.ticket_numbers:
            plan.unmappable.append(
                f"{p.surname}/{p.given_name}: {len(p.ticket_numbers)} "
                f"ticket_numbers has no column yet."
            )

    for s in message.segments:
        try:
            departure_time = _parse_hhmm(s.departure_time_raw)
            arrival_time = _parse_hhmm(s.arrival_time_raw)
        except ValueError as e:
            plan.unmappable.append(
                f"Segment {s.flight_number} {s.date_raw}: {e}"
            )
            continue

        plan.segments.append(SegmentPlan(
            airline_code=s.airline_code,
            flight_number=s.flight_number,
            rbd_class=s.reservation_booking_designator,
            flight_date_raw=s.date_raw,
            boarding_point=s.board_point,
            off_point=s.off_point,
            action_code=s.action_code,
            number_in_party=s.number_in_party,
            departure_time=departure_time,
            arrival_time=arrival_time,
            arrival_day_offset=s.arrival_day_offset,
        ))

    for osi in message.osi_elements:
        name_ref = getattr(osi, "name", None)
        passenger_index = None
        if name_ref is not None:
            passenger_index = _find_passenger_index(
                plan.passengers, name_ref.surname, name_ref.given_name, name_ref.title
            )

        if isinstance(osi, EmailContactElement):
            plan.osi_entries.append(OsiPlan(
                airline_code=osi.airline_code,
                information_text=f"EMAIL: {osi.email}",
                passenger_index=passenger_index,
            ))
        elif isinstance(osi, DobElement):
            plan.osi_entries.append(OsiPlan(
                airline_code=osi.airline_code,
                information_text=f"DOB: {osi.date_of_birth_raw}",
                passenger_index=passenger_index,
            ))
        elif isinstance(osi, OsiPassengerTypeFlagElement):
            plan.osi_entries.append(OsiPlan(
                airline_code=osi.airline_code,
                information_text=f"PASSENGER TYPE: {osi.passenger_type}",
                passenger_index=passenger_index,
            ))
        else:
            plan.unmappable.append(
                f"OSI element type {type(osi).__name__} has no mapping "
                f"yet: {osi.raw!r}"
            )

    for a in message.automated_ssrs:
        if isinstance(a, (AutomatedSsrElement, SsrPassengerTypeFlagElement)):
            name_ref = getattr(a, "name", None)
            passenger_index = None
            if name_ref is not None and hasattr(name_ref, "surname"):
                passenger_index = _find_passenger_index(
                    plan.passengers, name_ref.surname, name_ref.given_name, name_ref.title
                )
            ssr_code = getattr(a, "ssr_code", None) or "----"
            plan.ssr_entries.append(SsrPlan(
                ssr_code=ssr_code,
                airline_code=a.airline_code,
                action_code=getattr(a, "action_code", None),
                free_text=getattr(a, "free_text", None) or a.raw,
                passenger_index=passenger_index,
            ))
        else:
            plan.unmappable.append(
                f"SSR-family element type {type(a).__name__} has no "
                f"mapping yet: {a.raw!r}"
            )

    if message.group_fare_info:
        plan.unmappable.append(
            f"{len(message.group_fare_info)} group_fare_info entries have no mapping yet."
        )
    if message.group_seat_requests:
        plan.unmappable.append(
            f"{len(message.group_seat_requests)} group_seat_requests entries have no mapping yet."
        )
    if message.name_changes:
        plan.unmappable.append(
            f"{len(message.name_changes)} name_changes have no mapping yet."
        )
    if message.group_placeholders:
        plan.unmappable.append(
            f"{len(message.group_placeholders)} group_placeholders have no mapping yet."
        )
    if message.party_count_notices:
        plan.unmappable.append(
            f"{len(message.party_count_notices)} party_count_notices have no mapping yet."
        )
    if message.contact_addresses:
        plan.unmappable.append(
            f"{len(message.contact_addresses)} contact_addresses have no mapping yet."
        )
    if message.unrecognized_lines:
        plan.unmappable.append(
            f"{len(message.unrecognized_lines)} unrecognized_lines in the source message."
        )

    return plan


def save_booking_message(plan: BookingSavePlan) -> Pnr:

    if not plan.pnrs:
        raise ValueError("Plan has no PNR to save.")

    # Only the first record locator becomes the "primary" PNR
    primary_pnr_row = None
    for pp in plan.pnrs:
        row = Pnr(
            PNR_Code=pp.pnr_code,
            Booking_Office_Code=pp.booking_office_code,
            POS_Travel_Agent_ID=pp.pos_travel_agent_id,
            POS_City_Code=pp.pos_city_code,
            POS_User_Type=pp.pos_user_type,
            source="parsed",
        )
        db.session.add(row)
        if primary_pnr_row is None:
            primary_pnr_row = row

    db.session.flush()  # assigns PNR_ID without committing yet

    passenger_rows: list[Passenger] = []
    for pp in plan.passengers:
        row = Passenger(
            PNR_ID=primary_pnr_row.PNR_ID,
            Family_Name=pp.family_name,
            First_Name_Middle_Name=pp.first_name_middle_name,
            Title=pp.title,
            Number_In_Party=pp.number_in_party,
            Passenger_Type=pp.passenger_type,
            Email=pp.email,
            Date_Of_Birth_Raw=pp.date_of_birth_raw,
            Foid=pp.foid,
        )
        db.session.add(row)
        passenger_rows.append(row)

    db.session.flush()

    for sp in plan.segments:
        db.session.add(FlightSegment(
            PNR_ID=primary_pnr_row.PNR_ID,
            Airline_Code=sp.airline_code,
            Flight_Number=sp.flight_number,
            RBD_Class=sp.rbd_class,
            Flight_Date=None,  # date_raw has no year -- see Flight_Date_Raw
            Flight_Date_Raw=sp.flight_date_raw,
            Boarding_Point=sp.boarding_point,
            Off_Point=sp.off_point,
            Action_Code=sp.action_code,
            Number_In_Party=sp.number_in_party,
            Departure_Time=sp.departure_time,
            Arrival_Time=sp.arrival_time,
            Arrival_Day_Offset=sp.arrival_day_offset,
        ))

    for op in plan.osi_entries:
        passenger_id = (
            passenger_rows[op.passenger_index].Passenger_ID
            if op.passenger_index is not None else None
        )
        db.session.add(Osi(
            PNR_ID=primary_pnr_row.PNR_ID,
            Passenger_ID=passenger_id,
            Airline_Code=op.airline_code,
            Information_Text=op.information_text,
        ))

    for sp in plan.ssr_entries:
        passenger_id = (
            passenger_rows[sp.passenger_index].Passenger_ID
            if sp.passenger_index is not None else None
        )
        db.session.add(Ssr(
            PNR_ID=primary_pnr_row.PNR_ID,
            Passenger_ID=passenger_id,
            Segment_ID=None,  # no segment-level linkage in the parsed data yet
            SSR_Code=sp.ssr_code,
            Airline_Code=sp.airline_code,
            Action_Code=sp.action_code,
            Free_Text=sp.free_text,
        ))

    db.session.commit()
    return primary_pnr_row