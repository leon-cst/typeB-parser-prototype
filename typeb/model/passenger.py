from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class TicketNumberRecord(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    ticket_number: str
    airline_code: str
    segments: list[str]


class BookingPassenger(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    surname: str
    given_name: str | None
    title: str | None
    passenger_type: str
    seat_modifiers: list[str]
    email: str | None
    date_of_birth_raw: str | None
    foid: str | None
    ticket_numbers: list[TicketNumberRecord] = []