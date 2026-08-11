import pytest
from typeb.model.envelope import RecordLocator


def test_record_locator_booking_office_decomposed():
    rl = RecordLocator.parse("PARPA 115Y10AUG")
    assert rl.booking_office == "PARPA"
    assert rl.booking_office_city == "PAR"
    assert rl.booking_office_designator == "PA"


def test_record_locator_booking_office_three_char_designator_with_slash():
    rl = RecordLocator.parse("DPS/ABC QUAGUA")
    assert rl.booking_office == "DPS/ABC"
    assert rl.booking_office_city == "DPS"
    assert rl.booking_office_designator == "ABC"


def test_record_locator_booking_office_malformed_raises():
    with pytest.raises(ValueError, match="doesn't match"):
        RecordLocator.parse("PA CPNR1G")