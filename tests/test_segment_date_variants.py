import pytest

from typeb.elements.errors import ElementParseError
from typeb.elements.segment import parse_segment_element, render_segment_element
from typeb.elements.tokenizer import ElementKind, classify_line
from typeb.messages.booking import parse_booking_message


# --------------------------------------------------------------------------
# Tokenizer: reglue a SEGMENT/ARRIVAL first token that got split from its
# date by a space (annotation-document spacing artifact, not real wire
# format).
# --------------------------------------------------------------------------

def test_classify_reglues_split_date_before_matching_segment():
    assert classify_line("XX002F 15APR KULLHR RR1") == ElementKind.SEGMENT


def test_classify_glued_date_unaffected():
    assert classify_line("8G083F24SEP CGKDPS NN1 0910 1015") == ElementKind.SEGMENT


def test_classify_split_date_does_not_affect_name_lines():
    assert classify_line("1RAHARJO/BAMBANGMR") == ElementKind.NAME


def test_reglue_does_not_fire_on_genuinely_unrelated_two_token_lines():
    # A line that happens to have a bare-looking date-shaped second
    # token but isn't actually a split SEGMENT/ARRIVAL first field.
    assert classify_line("SSR GRPF TW YNO") == ElementKind.SSR


# --------------------------------------------------------------------------
# SEGMENT: optional 2-digit year suffix on the date (REQ03 section 9
# item 7, bilateral agreement).
# --------------------------------------------------------------------------

def test_segment_date_with_year():
    s = parse_segment_element("MZ123F08JAN26 CGKSIN SS2 0005 2355")
    assert s.date_raw == "08JAN26"


def test_segment_date_without_year_unaffected():
    s = parse_segment_element("8G083F24SEP CGKDPS NN1 0910 1015")
    assert s.date_raw == "24SEP"


# --------------------------------------------------------------------------
# SEGMENT: day-of-change indicator on arrival time (REQ03 section 9
# item 12: "/1" = +1 day, "/M1" = -1 day).
# --------------------------------------------------------------------------

def test_segment_arrival_day_change_positive():
    s = parse_segment_element("AV070F17AUG BOGFRA SS1 1105 0705/1")
    assert s.arrival_time_raw == "0705"
    assert s.arrival_day_offset == 1


def test_segment_arrival_day_change_negative():
    s = parse_segment_element("MZ123F08JAN26 CGKSIN SS2 0005 2355/M1")
    assert s.arrival_time_raw == "2355"
    assert s.arrival_day_offset == -1


def test_segment_arrival_day_change_multi_digit():
    s = parse_segment_element("MZ123J20FEB DPSSYD NN1 2340 0750/2")
    assert s.arrival_time_raw == "0750"
    assert s.arrival_day_offset == 2


def test_segment_no_day_change_indicator():
    s = parse_segment_element("8G083F24SEP CGKDPS NN1 0910 1015")
    assert s.arrival_day_offset is None


def test_segment_malformed_day_change_suffix_raises():
    with pytest.raises(ElementParseError, match="day-of-change indicator"):
        parse_segment_element("8G083F24SEP CGKDPS NN1 0910 1015/X")


def test_segment_day_change_round_trips_through_render():
    s = parse_segment_element("AV070F17AUG BOGFRA SS1 1105 0705/1")
    assert render_segment_element(s) == "AV070F17AUG BOGFRA SS1 1105 0705/1"


def test_segment_negative_day_change_round_trips_through_render():
    s = parse_segment_element("MZ123F08JAN26 CGKSIN SS2 0005 2355/M1")
    assert render_segment_element(s) == "MZ123F08JAN26 CGKSIN SS2 0005 2355/M1"


# --------------------------------------------------------------------------
# Full messages -- REQ03's own worked examples plus the real messages
# that originally surfaced the date-split/day-offset/year gaps.
# --------------------------------------------------------------------------

def test_tktl_set_message_with_split_date_and_day_offset():
    raw = """\
QU BOGRMAV
.ZRHRMLX 031540
ZRHLX AB 1458BC
1VALDERRAMA/JMR
AV070F 17AUG BOGFRA SS1/1105 0705/1
SSR TKTL AV SS/BOG 1700/12AUG
OSI AV CTCH BOG 242159"""
    msg = parse_booking_message(raw)
    assert len(msg.segments) == 1
    assert msg.segments[0].arrival_day_offset == 1
    assert msg.unrecognized_lines == []


def test_reconfirmation_message_with_split_date():
    raw = """\
QU KULRMXX
.HDGRMYY 141540
HDQYY YALUUW
1DENNIS/MAXINEMS
XX002F 15APR KULLHR RR1
OSI XX CTCA KUL RITZ CARLTON HTL"""
    msg = parse_booking_message(raw)
    assert msg.segments[0].action_code == "RR"
    assert msg.unrecognized_lines == []


def test_sold_and_reconfirmed_message_with_split_dates():
    raw = """\
QU KULRMXX
.HDQRMYY 131540
HDQYY PNRCO
1DENIS/MAXMS
XX1145F 14APR PENKUL RR1
XX002F 15APR KULLHR SS1/1000 1045"""
    msg = parse_booking_message(raw)
    assert [s.action_code for s in msg.segments] == ["RR", "SS"]
    assert msg.unrecognized_lines == []