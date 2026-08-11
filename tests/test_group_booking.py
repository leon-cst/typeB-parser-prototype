import pytest

from typeb.elements.errors import ElementParseError
from typeb.elements.name import parse_name_element, render_name_element
from typeb.elements.osi import parse_osi_line
from typeb.elements.ssr import parse_ssr_line
from typeb.messages.booking import parse_booking_message
from typeb.model.elements import NameElement, NameReference


def test_name_group_shape():
    n = parse_name_element("30SITA/TOUR")
    assert n.is_group_placeholder is True
    assert n.surname == "SITA"
    assert n.group_name_suffix == "TOUR"
    assert render_name_element(n) == "30SITA/TOUR"


def test_name_no_slash_placeholder_still_unaffected():
    n = parse_name_element("6SEAMEN")
    assert n.is_group_placeholder is True
    assert n.group_name_suffix is None
    assert render_name_element(n) == "6SEAMEN"


def test_ssr_grpf_bare():
    e = parse_ssr_line("SSR GRPF TW YNO")
    assert e.airline_code == "TW"
    assert e.status_code == "YNO"
    assert e.detail is None


def test_ssr_grpf_with_detail():
    e = parse_ssr_line("SSR GRPF TW YNO PARNYCSTL FRF 3590")
    assert e.status_code == "YNO"
    assert e.detail == "PARNYCSTL FRF 3590"


def test_ssr_gpst():
    e = parse_ssr_line("SSR GPST TW NN30 JFKSTL0209Y11AUG")
    assert e.airline_code == "TW"
    assert e.action_code == "NN"
    assert e.number_in_party == 30
    assert e.segment_reference_raw == "JFKSTL0209Y11AUG"


def test_ssr_tktl_set_shape():
    e = parse_ssr_line("SSR TKTL AV SS/BOG 1700/12AUG")
    assert e.status_code == "SS"
    assert e.city_code == "BOG"
    assert e.time_raw == "1700"
    assert e.date_raw == "12AUG"
    assert e.removal_note is None


def test_ssr_tktl_removal_shape():
    e = parse_ssr_line("SSR TKTL AV SS//BOG NOW TKTD")
    assert e.status_code == "SS"
    assert e.city_code == "BOG"
    assert e.time_raw is None
    assert e.date_raw is None
    assert e.removal_note == "NOW TKTD"


def test_ssr_tktl_unrecognized_shape_raises():
    with pytest.raises(ElementParseError, match="doesn't match either recognized shape"):
        parse_ssr_line("SSR TKTL AV GARBAGE")


def test_ssr_automated_generic_single_person_name():
    e = parse_ssr_line("SSR NSST LH NN1 FRAMXP 174520NOV-1SCHULTZ/LEO.WB")
    assert e.ssr_code == "NSST"
    assert isinstance(e.name, NameReference)
    assert e.name.surname == "SCHULTZ"
    assert e.free_text == "WB"


def test_ssr_automated_generic_group_name():
    e = parse_ssr_line(
        "SSR NSST TW NN5 JFKSTL 0209Y11AUG-5ARDMORE/BOB/SUE/TIM/TOM/TONY"
    )
    assert isinstance(e.name, NameElement)
    assert e.name.surname == "ARDMORE"
    assert len(e.name.people) == 5
    assert e.free_text is None


def test_ssr_unrecognized_code_still_raises_unrecognized():
    # A code that's neither a dedicated handler nor in the automated-
    # format whitelist must still be treated as genuinely unrecognized,
    # not silently guessed at.
    from typeb.elements.errors import UnrecognizedElementError

    with pytest.raises(UnrecognizedElementError):
        parse_ssr_line("SSR ZZZZ TW NN1 SOMETHING")


def test_osi_contact_address():
    o = parse_osi_line("OSI TW CTCA NYC HOLIDAY INN AGT ABC TRAVEL")
    assert o.airline_code == "TW"
    assert o.action_code == "CTCA"
    assert o.detail == "NYC HOLIDAY INN AGT ABC TRAVEL"


def test_osi_contact_address_ctch_variant():
    o = parse_osi_line("OSI AV CTCH BOG 242159")
    assert o.action_code == "CTCH"
    assert o.detail == "BOG 242159"


# --------------------------------------------------------------------------
# Full messages, converter batch "16) GROUP BOOKING (REQUEST FOR GROUP)"
# and related. Labels present in the source document (REC.LOC, NAME
# ELEMENT, etc.) and inconsistent spacing from its annotated-teaching
# layout are corrected to real wire format before use as fixtures --
# neither is transmitted content.
# --------------------------------------------------------------------------

def test_group_name_only():
    raw = """\
QU JFKRMTW
.PARRMPA 201521
PARPA 115Y10AUG
30SITA/TOUR
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720
SSR GRPF TW YNO
SSR GRPF TW YNO PARNYCSTL FRF 3590
SSR GPST TW NN30 JFKSTL0209Y11AUG"""
    msg = parse_booking_message(raw)
    assert msg.name_elements[0].is_group_placeholder is True
    assert len(msg.segments) == 2
    assert msg.unrecognized_lines == []


def test_group_with_all_individual_names():
    raw = """\
QU JFKRMTW
.PARRMPA 051355
PARPA 115Y10AUG
5ARDMORE 3BATES 5DRUMMOND 3ENGLER 4HAYRES 5ZIMMERMAN 5CLARK
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720
SSR GRPS TW TCP30 SITA/TOUR
SSR GRPF TW YNC
SSR GRPF TW YNC PARNYCSTL FRF 3590
OSI TW CTCA NYC HOLIDAY INN AGT ABC TRAVEL"""
    msg = parse_booking_message(raw)
    assert len(msg.name_elements) == 7
    assert msg.unrecognized_lines == []


def test_group_with_some_individual_names():
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
SSR GPST TW NN25 JFKSTL0209Y11AUG
SSR NSST TW NN5 JFKSTL 0209Y11AUG-5ARDMORE/BOB/SUE/TIM/TOM/TONY"""
    msg = parse_booking_message(raw)
    assert len(msg.passengers) == 5
    assert msg.unrecognized_lines == []


def test_group_with_tour_number():
    raw = """\
QU JFKRMIW
.ATLRMDL 111320
ATLDL 1467899AEG
40HARRIS
DL429Y16OCT ATLJFK HK40/1200 1900
TW943Y18OCT JFKSTL NN40/1400 1630
SSR GRPF TW YHVL IT90L 1234
SSR GRPF TW YHVL ATLNYCSTL USD 450 IT9DL 1234"""
    msg = parse_booking_message(raw)
    assert msg.unrecognized_lines == []


def test_ticketing_time_limit_set_message():
    raw = """\
QU BOGRMAV
.ZRHRMLX 031540
ZRHLX AB 1458BC
1VALDERRAMA/JMR
AV070F17AUG BOGFRA SS1/1105 0705
SSR TKTL AV SS/BOG 1700/12AUG
OSI AV CTCH BOG 242159"""
    msg = parse_booking_message(raw)
    assert msg.passengers[0].surname == "VALDERRAMA"
    assert msg.unrecognized_lines == []


def test_ticketing_time_limit_removal_message():
    raw = """\
QU BOGRMAV
.ZRHRMLX 031540
ZRHLX AB 1458BC
1VALDERRAMA/JMR
AV070F17AUG BOGFRA HK1
SSR TKTL AV SS//BOG NOW TKTD"""
    msg = parse_booking_message(raw)
    assert msg.unrecognized_lines == []


def test_reconfirmation_message():
    raw = """\
QU KULRMXX
.HDGRMYY 141540
HDQYY YALUUW
1DENNIS/MAXINEMS
XX002F15APR KULLHR RR1
OSI XX CTCA KUL RITZ CARLTON HTL"""
    msg = parse_booking_message(raw)
    assert msg.segments[0].action_code == "RR"
    assert msg.unrecognized_lines == []


def test_sold_and_reconfirmed_same_carrier():
    raw = """\
QU KULRMXX
.HDQRMYY 131540
HDQYY PNRCO
1DENIS/MAXMS
XX1145F14APR PENKUL RR1
XX002F15APR KULLHR SS1/1000 1045"""
    msg = parse_booking_message(raw)
    assert [s.action_code for s in msg.segments] == ["RR", "SS"]
    assert msg.unrecognized_lines == []


def test_arrival_elements_field_present_but_empty():
    # No reliable wire-level signal distinguishes arrival from segment
    # lines (REQ03 section 8 gives them identical grammar) -- see
    # typeb/messages/booking.py's comment. The field exists on the
    # model for when a real signal is found, but stays empty for now.
    raw = """\
QU JFKRMTW
.PARRMPA 201521
PARPA 115Y10AUG
30SITA/TOUR
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720"""
    msg = parse_booking_message(raw)
    assert msg.arrival_elements == []
    assert len(msg.segments) == 2