"""
Output model for the cross-reference layer -- see
typeb.elements.cross_reference for the function that builds these.

"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BookingPassenger(BaseModel):
    """One passenger, fully assembled from a NAME element's Person plus
    every OSI/SSR element that references them by name.
    """
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True, str_to_upper=True)

    surname: str
    given_name: str | None
    title: str | None
    passenger_type: str  # "ADT" | "CHD" | "INF"
    seat_modifiers: list[str]  # EXST/CBBG, inherited from the owning NameElement
    email: str | None
    date_of_birth_raw: str | None
    foid: str | None
    ticket_numbers: list[str] = []