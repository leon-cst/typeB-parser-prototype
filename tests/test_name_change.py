"""
End-to-end CHNT (name change) tests. Fixtures are the 3 real name-
change messages provided directly by Vy -- not REQ03's own worked
examples, per explicit scope instruction.

REQ03 section 25 p.67 -- the page these 3 messages are transcribed
from -- states two retention requirements checked here:
  1. A special service (SSR) tied to a changed name must be retained,
     not dropped, unless explicitly cancelled.
  2. OSI TCP carries the total party count and any names not in the
     NAME element; that's its entire purpose in these messages.

Unit tests for the underlying split_name_change_boundary() logic live
in test_elements.py, alongside the rest of name.py's tests.
"""
from typeb.messages.booking import parse_booking_message


def test_simple_name_swap_non_group():
    # AAAAA/RMR -> BBBBB/SMR, with OSI TCP names not re-included
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
1AAAAA/RMR
CHNT
1BBBBB/SMR
SJ326F15FEB CGKSIN HK1
OSI SJ TCP3 1CCCCC/KMR 1DDDDD/ZMR
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [ne.raw for ne in msg.name_elements] == ["1AAAAA/RMR"]
    assert [ne.raw for ne in msg.replacement_name_elements] == ["1BBBBB/SMR"]

    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "BBBBB"
    assert msg.passengers[0].given_name == "S"
    assert msg.passengers[0].title == "MR"

    # REQ03 section 25 p.67: OSI TCP carries the total party count and
    # any names not in the NAME element -- must survive parsing.
    assert len(msg.party_count_notices) == 1
    notice = msg.party_count_notices[0]
    assert notice.airline_code == "SJ"
    assert notice.total_party_count == 3
    assert [n.surname for n in notice.names] == ["CCCCC", "DDDDD"]

    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_bare_surname_reduce_with_correction():
    # PNR had 2GREEN 1ALLEN, corrected to 1GREEN 1MILLER 1ALLEN.
    # OSI TCP references a bare surname ("1ALLEN", no slash).
    raw = """\
QU JKTRMMZ
.SINRM1B 102025
SIN1B 134670PRR
2GREEN
CHNT
1GREEN 1MILLER
MZ453Y24MAY CGKSYD HK2
OSI YY TCP3 1ALLEN
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [ne.raw for ne in msg.name_elements] == ["2GREEN"]
    assert [ne.raw for ne in msg.replacement_name_elements] == ["1GREEN", "1MILLER"]

    # Per the message's own note: 1GREEN/1MILLER deliberately excluded
    # from the OSI TCP list -- only total_party_count has to be right,
    # names may be partial. Still must survive parsing intact.
    assert len(msg.party_count_notices) == 1
    notice = msg.party_count_notices[0]
    assert notice.airline_code == "YY"
    assert notice.total_party_count == 3
    assert [n.surname for n in notice.names] == ["ALLEN"]

    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_name_change_retains_vgml_for_old_name():
    # DDDDD/MRS -> YYYYY/MRS. REQ03 section 25 p.67: a special service
    # tied to the changed name must be retained, not dropped, unless
    # explicitly cancelled -- this SSR VGML line must appear in output.
    raw = """\
QU JKTRMMZ
.SINRM1B 101210
SIN1B 11E231
1DDDDD/MRS
CHNT
1YYYYY/MRS
MZ352Y20MAY ORDBRU HK1
SSR VGML MZ XX1 ORDBRU0352Y20MAY-1DDDDD/MRS
OSI MZ TCP4 1AAAAA/JMR 1BBBBB/BMR 1YYYYY/MRS
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [ne.raw for ne in msg.name_elements] == ["1DDDDD/MRS"]
    assert [ne.raw for ne in msg.replacement_name_elements] == ["1YYYYY/MRS"]

    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "YYYYY"
    assert msg.passengers[0].title == "MRS"

    assert len(msg.automated_ssrs) == 1
    assert msg.automated_ssrs[0].raw == (
        "SSR VGML MZ XX1 ORDBRU0352Y20MAY-1DDDDD/MRS"
    )

    assert len(msg.party_count_notices) == 1
    notice = msg.party_count_notices[0]
    assert notice.airline_code == "MZ"
    assert notice.total_party_count == 4
    assert [n.surname for n in notice.names] == ["AAAAA", "BBBBB", "YYYYY"]

    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_no_chnt_means_no_name_change():
    raw = """\
QU JKTRMMZ
.SINRM1B 102025
SIN1B 11E231
1AAAAA/JMR 1BBBBB/BMR 1CCCCC/MR 1DDDDD/MRS
MZ352Y20MAY ORDBRU HK4
SSR VGML MZ HK3 ORDBRU0352Y20MY-1AAAAA/JMR
SSR VGML MZ/// 1BBBBB/BMR 1DDDDD/MRS
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is False
    assert msg.replacement_name_elements == []
    assert len(msg.name_elements) == 4
    assert len(msg.passengers) == 4
    assert len(msg.automated_ssrs) == 2


def test_chnt_need_not_immediately_follow_the_name_line():
    # CHNT can appear after intervening SEGMENT/SSR/OSI lines -- the
    # NAME/CHNT lines just need to be in the right relative order.
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
1AAAAA/RMR
SJ326F15FEB CGKSIN HK1
CHNT
1BBBBB/SMR
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [ne.raw for ne in msg.name_elements] == ["1AAAAA/RMR"]
    assert [ne.raw for ne in msg.replacement_name_elements] == ["1BBBBB/SMR"]