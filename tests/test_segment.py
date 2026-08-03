import pytest

from typeb.elements.errors import ElementParseError
from typeb.elements.segment import parse_segment_element


def test_segment_with_times_spaced_form():
    # REQ03 p.9-10 canonical shape
    s = parse_segment_element("8G083F24SEP CGKDPS NN1 0910 1015")
    assert s.airline_code == "8G"
    assert s.flight_number == "083"
    assert s.reservation_booking_designator == "F"
    assert s.date_raw == "24SEP"
    assert s.board_point == "CGK"
    assert s.off_point == "DPS"
    assert s.action_code == "NN"
    assert s.number_in_party == 1
    assert s.departure_time_raw == "0910"
    assert s.arrival_time_raw == "1015"


def test_segment_no_times():
    s = parse_segment_element("SJ920Y15FEB SINAMS XX1")
    assert s.airline_code == "SJ"
    assert s.flight_number == "920"
    assert s.reservation_booking_designator == "Y"
    assert s.date_raw == "15FEB"
    assert s.board_point == "SIN"
    assert s.off_point == "AMS"
    assert s.action_code == "XX"
    assert s.number_in_party == 1
    assert s.departure_time_raw is None
    assert s.arrival_time_raw is None


def test_segment_malformed_first_token_raises():
    with pytest.raises(ElementParseError, match="airline\\+flight\\+rbd\\+date"):
        parse_segment_element("NOTVALID CGKDPS NN1")


# --------------------------------------------------------------------------
# Glued action+count/departure-time form -- confirmed real by Vy's
# coworker (spec author), alongside the spaced REQ03 form.
# --------------------------------------------------------------------------

def test_segment_glued_action_count_departure_time():
    # The exact real-world line that originally failed to parse.
    s = parse_segment_element("8G191U28JUL DILDPS NN6/0910 1015")
    assert s.airline_code == "8G"
    assert s.flight_number == "191"
    assert s.reservation_booking_designator == "U"
    assert s.date_raw == "28JUL"
    assert s.board_point == "DIL"
    assert s.off_point == "DPS"
    assert s.action_code == "NN"
    assert s.number_in_party == 6
    assert s.departure_time_raw == "0910"
    assert s.arrival_time_raw == "1015"


def test_segment_glued_and_spaced_forms_produce_identical_results():
    # raw naturally differs (it's the literal input) -- everything else
    # should match exactly regardless of which form was used.
    glued = parse_segment_element("8G191U28JUL DILDPS NN6/0910 1015")
    spaced = parse_segment_element("8G191U28JUL DILDPS NN6 0910 1015")
    assert glued.model_dump(exclude={"raw"}) == spaced.model_dump(exclude={"raw"})


def test_segment_glued_form_without_arrival_time_still_rejected():
    # Only departure time glued on, no arrival time at all -- this is
    # NOT one of the two confirmed shapes (times are documented as
    # "both present or both absent"), so it should still raise rather
    # than silently accept a partial time pair.
    with pytest.raises(ElementParseError, match="expected 3 tokens"):
        parse_segment_element("8G191U28JUL DILDPS NN6/0910")


def test_segment_glued_form_wrong_time_digits_still_raises():
    # "091" (3 digits) doesn't match the glued shape's \d{4} requirement
    # at all, so this falls through to the generic token-count error --
    # still correctly rejected, just via a different (also accurate)
    # message than a 4-digit-but-wrong-value case would get.
    with pytest.raises(ElementParseError, match="expected 3 tokens"):
        parse_segment_element("8G191U28JUL DILDPS NN6/091 1015")


def test_segment_slash_in_wrong_position_not_treated_as_glued_form():
    # A stray '/' in the city-pair token should NOT be silently
    # "corrected" by the glue-detection logic -- it only ever inspects
    # the action+count token position.
    with pytest.raises(ElementParseError, match="city pair"):
        parse_segment_element("8G083F24SEP CGK/DPS NN1 0910 1015")