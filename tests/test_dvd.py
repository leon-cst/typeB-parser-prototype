"""
End-to-end DVD (Divide PNR, REQ03 section 24) tests. Fixtures are the
5 real messages provided directly by Vy, matching REQ03's own p.63-66
worked examples verbatim.

Unit tests for the OSI RLOC glued-shape parser live in test_osi.py.
"""
from pytest import raises

from typeb.elements.errors import ElementParseError
from typeb.messages.dvd import parse_dvd_message


def test_single_passenger_diverted_destination():
    raw = """\
QU CGKRMSJ
.HDQRM8G 101234
DVD
HDQ8G CPNRSJ/ABC/12345678/LON/1G/T/GB
1AAAAA/MR
SJ920Y15FEB SINAMS XX1
8G320Y15FEB CGKSIN HK1/1030 1210
SJ890Y15FEB SINLON SS1/1350 1610
OSI YY RLOC HDQ8GCPNRSJ"""

    msg = parse_dvd_message(raw)

    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "AAAAA"

    assert [s.action_code for s in msg.segments] == ["XX", "HK", "SS"]

    assert len(msg.original_locators) == 1
    assert msg.original_locators[0].glued_locator == "HDQ8GCPNRSJ"

    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_malformed_segment_line_excluded_not_fatal():
    # REQ03's own p.64 worked example -- the MZ800 segment line has no
    # action code. Rest of the message must still parse.
    raw = """\
QU CGKRMSJ
.HDQRM8G 201110
DVD
HDQ8G CPNRSJ/ABC/12345678/LON/1G/T/GB
1BBBBB/LMR 1CCCCC/NMR
SJ920Y 15FEB SINAMS XX2
MZ800Y15FEB SINZRH/1230 0130/1
OSI YY RLOC HDQ8GCPNRSJ"""

    msg = parse_dvd_message(raw)

    assert len(msg.passengers) == 2
    assert [s.action_code for s in msg.segments] == ["XX"]
    assert len(msg.original_locators) == 1

    assert len(msg.unrecognized_lines) == 1
    assert "SINZRH" in msg.unrecognized_lines[0].raw


def test_downstream_carrier_notification_no_original_locator():
    # Same underlying divide as the previous test, message sent to the
    # other carrier (MZ) instead of 8G -- no OSI RLOC line in this one.
    raw = """\
QU JKTRMMZ
.HDQRM8G 101530
DVD
HDQ8G CPNRSJ/ABC/12345678/LON/1G/T/GB
1BBBBB/LMR 1CCCCC/NMR
8G320Y15FEB CGKSIN HK2/1030 1210
MZ800Y15FEB SINZRH SS2/1230 0130/1"""

    msg = parse_dvd_message(raw)

    assert len(msg.passengers) == 2
    assert [s.action_code for s in msg.segments] == ["HK", "SS"]
    assert msg.original_locators == []
    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_divide_no_name_or_itinerary_change():
    raw = """\
QU CGKRMSJ
.JKTRMMZ 052039
DVD
JKTMZ CPNRMZ/ABC/12345678/LON/GT/T/GB
1BBBBB/MMR
SJ008Y15NOV LAXJFK HK1
OSI YY RLOC JKTMZAB26F6"""

    msg = parse_dvd_message(raw)

    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "BBBBB"
    assert msg.original_locators[0].glued_locator == "JKTMZAB26F6"
    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_divide_notifies_both_itinerary_carriers():
    # Same divide, two messages -- one to each carrier remaining on the
    # itinerary. Both point back at the same original locator.
    raw_kd = """\
QU CGKRMKD
.LAXRMMZ 011015
DVD
LAXMZ J9ABC6/ABC/11111111/LON/1G/T/GB
1LINTONG/G
KD062F13NOV DENORD XX1
MZ028F12NOV LAXDEN HK1/1430 1610
KD062F14NOV DENORD SS1/1430 1823
SJ104F 15NOV ORDLGA HK1/1530 2100
OSI YY RLOC LAXMZDWA9B5"""

    raw_sj = """\
QU CGKRMSJ
.LAXRMMZ 011015
DVD
LAXMZ J9ABC6/ABC/11111111/LON/1G/T/GB
1LINTONG/G
KD062F14NOV DENORD HK1/1430 1610
SJ104F15NOV ORDLGA HK1
OSI YY RLOC LAXMZDWA9B5"""

    msg_kd = parse_dvd_message(raw_kd)
    msg_sj = parse_dvd_message(raw_sj)

    assert [s.action_code for s in msg_kd.segments] == ["XX", "HK", "SS", "HK"]
    assert [s.action_code for s in msg_sj.segments] == ["HK", "HK"]

    assert (
        msg_kd.original_locators[0].glued_locator
        == msg_sj.original_locators[0].glued_locator
        == "LAXMZDWA9B5"
    )


def test_wrong_identifier_rejected():
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
1AAAAA/RMR
SJ920Y15FEB SINAMS HK1
NNNN"""
    with raises(ElementParseError, match="non-DVD"):
        parse_dvd_message(raw)