"""
Output model for the cross-reference layer -- see
typeb.elements.cross_reference for the function that builds these.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class BookingPassenger(BaseModel):
    """One passenger, fully assembled from a NAME element's Person plus
    every OSI/SSR element that references them by name. Distinct from
    Person (the raw per-NAME-line unit, before cross-referencing) --
    this is the cross-reference step's output, not something a
    single-element parser produces on its own.

    passenger_type is derived, not stated directly anywhere in the wire
    format:
      - "INF" if matched to an SSR INFT or OSI ... INF ... line
      - "CHD" if matched to an SSR CHLD or OSI ... CHD ... line
      - "ADT" otherwise (the default -- no code says "this is an adult",
        adult is simply the absence of a child/infant signal)
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