"""
Element parser tests, built from real REQ02/REQ03 worked examples.
"""
import pytest

from typeb.elements.availability import parse_availability_line
from typeb.elements.errors import ElementParseError
from typeb.elements.name import parse_name_element, parse_name_reference, split_name_change_boundary
from typeb.elements.recap import parse_recap_line
from typeb.elements.segment import parse_segment_element


# --------------------------------------------------------------------------
# NAME -- all five worked examples transcribed directly from REQ03 section 9
# --------------------------------------------------------------------------

def test_name_single_person_glued_title():
    # "MR. JEAN DUVAL" -> 1DUVAL/JEANMR
    n = parse_name_element("1DUVAL/JEANMR")
    assert n.number_in_party == 1
    assert n.surname == "DUVAL"
    assert len(n.people) == 1
    assert n.people[0].given_name == "JEAN"
    assert n.people[0].title == "MR"
    assert n.is_group_placeholder is False


def test_name_single_person_first_and_middle_with_separate_title():
    # "MR. EDWARD CHARLES JONES" -> 1JONES/EDWARDCHARLES/MR
    n = parse_name_element("1JONES/EDWARDCHARLES/MR")
    assert n.surname == "JONES"
    assert len(n.people) == 1
    assert n.people[0].given_name == "EDWARDCHARLES"
    assert n.people[0].title == "MR"


def test_name_no_given_name_title_only():
    # "MISS. DUVALIER" -> 1DUVALIER/MISS
    n = parse_name_element("1DUVALIER/MISS")
    assert n.surname == "DUVALIER"
    assert len(n.people) == 1
    assert n.people[0].given_name is None
    assert n.people[0].title == "MISS"


def test_name_shared_surname_group_no_titles():
    # "E FORD, B FORD, C FORD" -> 3FORD/E/B/C
    n = parse_name_element("3FORD/E/B/C")
    assert n.number_in_party == 3
    assert n.surname == "FORD"
    assert len(n.people) == 3
    assert [p.given_name for p in n.people] == ["E", "B", "C"]
    assert all(p.title is None for p in n.people)


def test_name_no_given_name_title_only_mrs():
    # "MRS. B KHOWRY" -> 1KHOWRY/MRS (initial "B" dropped upstream --
    # nothing for this parser to reconstruct)
    n = parse_name_element("1KHOWRY/MRS")
    assert n.surname == "KHOWRY"
    assert n.people[0].given_name is None
    assert n.people[0].title == "MRS"


def test_name_group_placeholder_no_individual_names():
    # "6SEAMEN" -- group booking before individual names are known
    n = parse_name_element("6SEAMEN")
    assert n.number_in_party == 6
    assert n.surname == "SEAMEN"
    assert n.people == []
    assert n.is_group_placeholder is True


def test_name_mstr_title_as_separate_token():
    n = parse_name_element("1PRATAMA/ARIELUCY/MSTR")
    assert n.surname == "PRATAMA"
    assert n.people[0].given_name == "ARIELUCY"
    assert n.people[0].title == "MSTR"


def test_name_two_person_group_no_titles():
    # REQ03 p.25-26 (teaching labels stripped, per test_envelope.py note).
    # Under the corrected grammar this is a valid 2-person shared-surname
    # group (BORGE/A and BORGE/D), not a single malformed name -- my
    # first attempt at this parser got this case wrong.
    n = parse_name_element("2BORGE/A/D")
    assert n.number_in_party == 2
    assert n.surname == "BORGE"
    assert len(n.people) == 2
    assert [p.given_name for p in n.people] == ["A", "D"]
    assert all(p.title is None for p in n.people)


def test_name_missing_leading_digits_raises():
    with pytest.raises(ElementParseError, match="number in party"):
        parse_name_element("RAHARJO/BAMBANGMR")


def test_name_distinct_surnames_adult_and_infant_now_resolves():
    # This was the original real-world divergent shape that used to
    # raise (number_in_party=2, 5 tokens after the surname). Once Logic B
    # (distinct surnames, boundaries found by titles) was added per
    # explicit instruction, this correctly resolves into the two real
    # people it always represented -- confirmed by matching SSR FOID/
    # SSR INFT lines elsewhere in the same real message.
    n = parse_name_element("2KUSUMA/BUDISANTOSO/MR/ANGGARA/BAYIBUDI/MR")
    assert n.uses_distinct_surnames is True
    assert len(n.people) == 2
    assert n.people[0].surname == "KUSUMA"
    assert n.people[0].given_name == "BUDISANTOSO"
    assert n.people[0].title == "MR"
    assert n.people[1].surname == "ANGGARA"
    assert n.people[1].given_name == "BAYIBUDI"
    assert n.people[1].title == "MR"


def test_name_distinct_surnames_with_separator_titles():
    # The coworker-provided example this feature was actually requested
    # for.
    n = parse_name_element("2WIJAYA/RINAMAHARANI/MRS/SIREGAR/BAYIRINA/MSTR")
    assert n.uses_distinct_surnames is True
    assert len(n.people) == 2
    assert n.people[0].surname == "WIJAYA"
    assert n.people[0].given_name == "RINAMAHARANI"
    assert n.people[0].title == "MRS"
    assert n.people[1].surname == "SIREGAR"
    assert n.people[1].given_name == "BAYIRINA"
    assert n.people[1].title == "MSTR"


def test_name_distinct_surnames_with_glued_titles():
    # Same shape, but with titles glued onto the given name instead of
    # being their own token (e.g. "KEVINMR" instead of "KEVIN/MR").
    n = parse_name_element("2WIJAYA/RINAMAHARANIMRS/SIREGAR/BAYIRINAMSTR")
    assert n.uses_distinct_surnames is True
    assert n.people[0].given_name == "RINAMAHARANI"
    assert n.people[0].title == "MRS"
    assert n.people[1].given_name == "BAYIRINA"
    assert n.people[1].title == "MSTR"


def test_name_still_raises_on_genuinely_unresolvable_mixed_shape():
    # 3 people where 2 share a surname (FORD) and 1 has their own
    # (SIREGAR) -- mixes both shapes in one line. Not evidenced by any
    # example seen so far, so this must still raise, not guess.
    with pytest.raises(ElementParseError, match="Refusing to guess"):
        parse_name_element("3FORD/E/B/SIREGAR/BAYIRINA/MSTR")


def test_name_exst_seat_modifier():
    # REQ03 p.11: "Mr. Albert Dooley need Extra seat" -> number_in_party
    # is 2 (one real person + one phantom seat for EXST), not 2 people.
    n = parse_name_element("2DOOLEY/ALBERTMR/EXST")
    assert n.number_in_party == 2
    assert n.surname == "DOOLEY"
    assert len(n.people) == 1
    assert n.people[0].given_name == "ALBERT"
    assert n.people[0].title == "MR"
    assert n.seat_modifiers == ["EXST"]


def test_name_without_seat_modifier_has_empty_list():
    n = parse_name_element("1DUVAL/JEANMR")
    assert n.seat_modifiers == []


# --------------------------------------------------------------------------
# SEGMENT (booking context)
# --------------------------------------------------------------------------

def test_segment_with_times():
    # REQ03 p.49
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


def test_segment_without_times():
    # REQ03 p.63
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
# AVAILABILITY_LINE (AVN body)
# --------------------------------------------------------------------------

def test_availability_line():
    # REQ02 p.7
    a = parse_availability_line("AA800 F 01JUN CGKDPS")
    assert a.airline_code == "AA"
    assert a.flight_number == "800"
    assert a.reservation_booking_designator == "F"
    assert a.date_raw == "01JUN"
    assert a.board_point == "CGK"
    assert a.off_point == "DPS"


def test_availability_line_digit_led_airline():
    a = parse_availability_line("8G800 Y 01JUN CGKDPS")
    assert a.airline_code == "8G"
    assert a.board_point == "CGK"
    assert a.off_point == "DPS"


def test_availability_line_wrong_token_count_raises():
    with pytest.raises(ElementParseError, match="4 space-separated tokens"):
        parse_availability_line("AA800 F 01JUN")


# --------------------------------------------------------------------------
# RECAP_LINE (RVR body) -- two shapes, see typeb.elements.recap
# --------------------------------------------------------------------------

def test_recap_date_range_line():
    # REQ02 p.13 (not REQ03 -- RVR has no worked examples there at all,
    # only a one-line identifier-table mention on p.8)
    r = parse_recap_line("8G407/16JUN26-30DEC26/1234567")
    assert r.airline_code == "8G"
    assert r.flight_number == "407"
    assert r.date_range_raw == "16JUN26-30DEC26"
    assert r.frequency_raw == "1234567"


def test_recap_date_range_malformed_date_range_raises():
    # 2 slashes (correctly dispatches to the date-range parser), but the
    # middle field is missing the dash separating start/end dates.
    with pytest.raises(ElementParseError, match="ddMMMyy-ddMMMyy"):
        parse_recap_line("8G407/16JUN26/1234567")


def test_recap_single_date_line_with_route():
    # REQ02 p.14, one of two concrete worked examples in the same message
    r = parse_recap_line("8G123/16JUN26 CGKSIN")
    assert r.airline_code == "8G"
    assert r.flight_number == "123"
    assert r.date_raw == "16JUN26"
    assert r.route == "CGKSIN"


def test_recap_single_date_line_without_route_is_all():
    # REQ02 p.13: "Route tidak perlu di isi (berarti all)" -- route
    # omitted entirely is valid, not an error, and means "ALL".
    r = parse_recap_line("8G123/16JUN26")
    assert r.route == "ALL"


def test_recap_ambiguous_slash_count_raises():
    with pytest.raises(ElementParseError, match="expected 1.*or 2"):
        parse_recap_line("8G123/16JUN26/EXTRA/EXTRA")


# --------------------------------------------------------------------------
# split_name_change_boundary -- CHNT (REQ03 sections 25/30)
# --------------------------------------------------------------------------

def test_split_name_change_no_chnt_returns_everything_as_current():
    passengers, changes = split_name_change_boundary(["1AAAAA/RMR"])
    assert [n.raw for n in passengers] == ["1AAAAA/RMR"]
    assert changes == []


def test_split_name_change_single_pair():
    passengers, changes = split_name_change_boundary(
        ["1AAAAA/RMR", "CHNT", "1AAAAA/RMR 1BBBBB/SMR"]
    )
    assert [n.raw for n in passengers] == ["1AAAAA/RMR"]
    assert len(changes) == 1
    assert changes[0].old.raw == "1AAAAA/RMR"
    assert changes[0].new.raw == "1BBBBB/SMR"


def test_split_name_change_multiple_pairs_unambiguous_with_multiple_passengers():
    # The scenario the old positional format couldn't express: two
    # passengers in the same booking both changing names, explicitly
    # paired so there's no ambiguity about who becomes who.
    passengers, changes = split_name_change_boundary(
        [
            "1AAAAA/RMR 1BBBBB/BMR",
            "CHNT",
            "1AAAAA/RMR 1CCCCC/CMR",
            "1BBBBB/BMR 1DDDDD/DMR",
        ]
    )
    assert [n.raw for n in passengers] == ["1AAAAA/RMR", "1BBBBB/BMR"]
    assert len(changes) == 2
    assert (changes[0].old.raw, changes[0].new.raw) == ("1AAAAA/RMR", "1CCCCC/CMR")
    assert (changes[1].old.raw, changes[1].new.raw) == ("1BBBBB/BMR", "1DDDDD/DMR")


def test_split_name_change_pair_line_wrong_group_count_raises():
    with pytest.raises(ElementParseError, match="exactly 2 name groups"):
        split_name_change_boundary(["1AAAAA/RMR", "CHNT", "1BBBBB/SMR"])


def test_split_name_change_old_name_not_in_passenger_list_raises():
    with pytest.raises(ElementParseError, match="doesn't match any passenger"):
        split_name_change_boundary(
            ["1AAAAA/RMR", "CHNT", "1ZZZZZ/XMR 1BBBBB/SMR"]
        )


def test_split_name_change_no_names_before_chnt_raises():
    with pytest.raises(ElementParseError, match="no NAME line before"):
        split_name_change_boundary(["CHNT", "1AAAAA/RMR 1BBBBB/SMR"])


def test_split_name_change_no_names_after_chnt_raises():
    with pytest.raises(ElementParseError, match="no NAME line after"):
        split_name_change_boundary(["1AAAAA/RMR", "CHNT"])


def test_split_name_change_duplicate_chnt_raises():
    with pytest.raises(ElementParseError, match="more than one CHNT"):
        split_name_change_boundary(
            ["1AAAAA/RMR", "CHNT", "1AAAAA/RMR 1BBBBB/SMR", "CHNT", "1CCCCC/TMR"]
        )


# --------------------------------------------------------------------------
# parse_name_reference -- SSR/OSI embedded name references
# --------------------------------------------------------------------------

def test_name_reference_bare_surname_no_title_suffix():
    ref = parse_name_reference("1ALLEN")
    assert ref.surname == "ALLEN"
    assert ref.given_name is None
    assert ref.title is None


def test_name_reference_given_name_and_title_suffix_no_surname():
    # No slash, but INF is a recognized title -- resolved as given
    # name + title, not treated as a literal surname.
    ref = parse_name_reference("1BAYIBUDIINF")
    assert ref.surname is None
    assert ref.given_name == "BAYIBUDI"
    assert ref.title == "INF"


def test_name_reference_slash_shape_unaffected():
    ref = parse_name_reference("1KUSUMA/BUDISANTOSOMR")
    assert ref.surname == "KUSUMA"
    assert ref.given_name == "BUDISANTOSO"
    assert ref.title == "MR"