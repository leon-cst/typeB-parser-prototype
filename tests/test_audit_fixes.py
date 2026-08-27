import pytest

from typeb.elements.cross_reference import validate_party_size
from typeb.elements.errors import ElementParseError
from typeb.elements.name import parse_name_element
from typeb.elements.ssr import parse_ssr_line
from typeb.messages.booking import parse_booking_message


# --------------------------------------------------------------------------
# Bug: party-size validation excluded group placeholders from the count,
# producing a false-positive warning even when the numbers genuinely match.
# --------------------------------------------------------------------------

def test_group_placeholder_counts_toward_party_size():
    n = parse_name_element("9SEAMEN")
    validate_party_size([n], 9)  # doesn't raise


def test_group_placeholder_mismatch_raises():
    n = parse_name_element("9SEAMEN")
    with pytest.raises(ElementParseError, match="total party size of 9"):
        validate_party_size([n], 5)


def test_surname_only_placeholders_sum_correctly():
    # REQ03 section 7's "party not yet individually named" shape --
    # each of these is its own group placeholder (>=9, per the
    # no-title-below-9 rule); the total across all of them must count
    # toward the segment's party size.
    elements = [
        parse_name_element(tok)
        for tok in "9ARDMORE 9BATES 9DRUMMOND 9ENGLER 9HAYRES 9ZIMMERMAN 9CLARK".split()
    ]
    assert sum(e.number_in_party for e in elements) == 63
    validate_party_size(elements, 63)  # doesn't raise


# --------------------------------------------------------------------------
# Bug: identical warnings fired once per matching segment instead of once
# per distinct issue.
# --------------------------------------------------------------------------

def test_warnings_deduplicated_across_segments():
    raw = """\
QU JFKRMTW
.PARRMPA 051355
PARPA 115Y10AUG
9ARDMORE 9BATES 9DRUMMOND 9ENGLER 9HAYRES
9ZIMMERMAN 9CLARK
DL119Y10AUG ORYJFK HK63/1435 1700
TW209Y11AUG JFKSTL NN63/1550 1720
SSR GRPS TW TCP63 SITA/TOUR
SSR GRPF TW YNC
SSR GRPF TW YNC PARNYCSTL FRF 3590
OSI TW CTCA NYC HOLIDAY INN AGT ABC TRAVEL"""
    msg = parse_booking_message(raw)
    # 63 declared across 7 groups matches both segments' 63 seats
    # exactly -- no warning should fire at all now that the count bug
    # is fixed, let alone fire twice.
    assert msg.warnings == []


# --------------------------------------------------------------------------
# Bug: SSR GPST only accepted the spaced action+count/segment-reference
# form, not the glued form real message traffic actually uses.
# --------------------------------------------------------------------------

def test_ssr_gpst_glued_form():
    e = parse_ssr_line("SSR GPST TW NN25JFKSTL0209Y11AUG")
    assert e.action_code == "NN"
    assert e.number_in_party == 25
    assert e.segment_reference_raw == "JFKSTL0209Y11AUG"


def test_ssr_gpst_spaced_form_unaffected():
    e = parse_ssr_line("SSR GPST TW NN30 JFKSTL0209Y11AUG")
    assert e.action_code == "NN"
    assert e.number_in_party == 30
    assert e.segment_reference_raw == "JFKSTL0209Y11AUG"


# --------------------------------------------------------------------------
# New: group_placeholders surfaces group/placeholder NAME data that
# cross_reference_passengers correctly excludes from `passengers` (no
# real given name exists to build a BookingPassenger from).
# --------------------------------------------------------------------------

def test_group_placeholders_field_surfaces_surname_only_groups():
    raw = """\
QU JFKRMTW
.PARRMPA 051355
PARPA 115Y10AUG
9ARDMORE 9BATES 9DRUMMOND 9ENGLER 9HAYRES
9ZIMMERMAN 9CLARK
DL119Y10AUG ORYJFK HK63/1435 1700
TW209Y11AUG JFKSTL NN63/1550 1720
SSR GRPS TW TCP63 SITA/TOUR
SSR GRPF TW YNC
SSR GRPF TW YNC PARNYCSTL FRF 3590
OSI TW CTCA NYC HOLIDAY INN AGT ABC TRAVEL"""
    msg = parse_booking_message(raw)
    assert msg.passengers == []
    assert len(msg.group_placeholders) == 7
    assert sum(g.number_in_party for g in msg.group_placeholders) == 63
    assert {g.surname for g in msg.group_placeholders} == {
        "ARDMORE", "BATES", "DRUMMOND", "ENGLER", "HAYRES", "ZIMMERMAN", "CLARK",
    }


def test_group_placeholders_field_surfaces_tour_group_name():
    raw = """\
QU JFKRMTW
.PARRMPA 051355
PARPA 115Y10AUG
25SITA/TOUR 5ARDMORE/BOB/SUE/TIM/TOM/TONY
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720
SSR GRPS TW TCP30 SITA/TOUR
SSR GRPF TW YLE13/GV30
SSR GRPF TW YLE13/GV30 PARNYCSTL PRF 3590
SSR GPST TW NN25JFKSTL0209Y11AUG
SSR NSST TW NN5 JFKSTL 0209Y11AUG-5ARDMORE/BOB/SUE/TIM/TOM/TONY"""
    msg = parse_booking_message(raw)
    assert len(msg.passengers) == 5  # the named Ardmore family
    assert len(msg.group_placeholders) == 1
    assert msg.group_placeholders[0].surname == "SITA"
    assert msg.group_placeholders[0].number_in_party == 25
    assert msg.group_placeholders[0].group_name_suffix == "TOUR"
    assert msg.unrecognized_lines == []