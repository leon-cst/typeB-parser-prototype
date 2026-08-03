from __future__ import annotations

from typeb.model.envelope import Address, CommReference, RecordLocator

_POS_FIELD_NAMES = (
    "travel_agent_city_code",
    "iata_number",
    "city_airport_code",
    "crs_code",
    "user_type",
    "iso_country_code",
    "iso_currency_code",
    "duty_code",
    "user_id_pss",
    "point_of_departure",
)


def render_address(address: Address) -> str:
    return f"{address.city_code}{address.office_code}{address.designator}"


def render_comm_reference(comm: CommReference) -> str:
    return f".{render_address(comm.origin)} {comm.date_time_raw}"


def render_record_locator(rl: RecordLocator) -> str:
    values = [getattr(rl, name) for name in _POS_FIELD_NAMES]
    while values and values[-1] is None:
        values.pop()
    pos_part = "".join(f"/{v or ''}" for v in values)
    return f"{rl.booking_office} {rl.location_of_record}{pos_part}"