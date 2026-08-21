"""
End-to-end CHNT (name change) tests, corrected format (REQ03 sections
25/30 as clarified by coworker): the full passenger list precedes
CHNT, and each line after CHNT is an explicit "OLDNAME NEWNAME" pair --
not two separate before/after blocks. This resolves the ambiguity the
original before/after-block reading had with multiple passengers (see
test_elements.py's split_name_change_boundary tests for the pairing
logic itself).

msg.passengers displays the OLD name for a renamed passenger's
identity (surname/given_name/title) -- other data (tickets, FOID, DOB)
still resolves normally regardless of whether a given SSR/OSI line on
the wire references the old or the new name.

Message 1 and 3 from the original 3-message batch are single-passenger
cases and are corrected here to the new pairing shape. Message 2
("2GREEN / CHNT / 1GREEN 1MILLER") was confirmed to be a different
scenario (a group placeholder splitting into named individuals, not a
name change) and isn't a CHNT fixture at all -- out of scope here.
"""
from typeb.messages.booking import parse_booking_message


def test_simple_name_swap_non_group():
    # AAAAA/RMR -> BBBBB/SMR, corrected to the OLDNAME NEWNAME pairing
    # shape. OSI TCP names not re-included, per the original message's
    # own note.
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
1AAAAA/RMR
CHNT
1AAAAA/RMR 1BBBBB/SMR
SJ326F15FEB CGKSIN HK1
OSI SJ TCP3 1CCCCC/KMR 1DDDDD/ZMR
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [ne.raw for ne in msg.name_elements] == ["1AAAAA/RMR"]
    assert len(msg.name_changes) == 1
    assert msg.name_changes[0].old.raw == "1AAAAA/RMR"
    assert msg.name_changes[0].new.raw == "1BBBBB/SMR"

    # passengers shows the OLD name as the identity
    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "AAAAA"
    assert msg.passengers[0].given_name == "R"
    assert msg.passengers[0].title == "MR"

    assert len(msg.party_count_notices) == 1
    notice = msg.party_count_notices[0]
    assert notice.airline_code == "SJ"
    assert notice.total_party_count == 3
    assert [n.surname for n in notice.names] == ["CCCCC", "DDDDD"]

    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_name_change_retains_vgml_for_old_name():
    # DDDDD/MRS -> YYYYY/MRS, corrected to the pairing shape. REQ03
    # section 25 p.67: a special service tied to the changed name must
    # be retained, not dropped, unless explicitly cancelled.
    raw = """\
QU JKTRMMZ
.SINRM1B 101210
SIN1B 11E231
1DDDDD/MRS
CHNT
1DDDDD/MRS 1YYYYY/MRS
MZ352Y20MAY ORDBRU HK1
SSR VGML MZ XX1 ORDBRU0352Y20MAY-1DDDDD/MRS
OSI MZ TCP4 1AAAAA/JMR 1BBBBB/BMR 1YYYYY/MRS
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [ne.raw for ne in msg.name_elements] == ["1DDDDD/MRS"]
    assert msg.name_changes[0].old.raw == "1DDDDD/MRS"
    assert msg.name_changes[0].new.raw == "1YYYYY/MRS"

    # passengers shows the OLD name -- even though the SSR VGML line
    # (kept for retention) references the old name and OSI TCP
    # references the new name, both resolve to this one record.
    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "DDDDD"
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


def test_ssr_referencing_new_name_still_resolves_to_old_name_display():
    # A ticket issued AFTER the rename references the new name on the
    # wire -- confirms resolution isn't old-name-only, and the
    # resolved record still displays under the old name.
    raw = """\
QU JKTRMMZ
.SINRM1B 101210
SIN1B 11E231
1DDDDD/MRS
CHNT
1DDDDD/MRS 1YYYYY/MRS
MZ352Y20MAY ORDBRU HK1
SSR TKNE MZ ORDBRU0352Y20MAY-1YYYYY/MRS.2051234567890C1
NNNN"""

    msg = parse_booking_message(raw)

    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "DDDDD"
    assert msg.passengers[0].ticket_numbers[0].ticket_number == "2051234567890C1"
    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_two_passengers_change_names_unambiguously():
    # The scenario the old before/after-block format couldn't express
    # without guessing: two passengers in one booking both change
    # names, explicitly paired -- no positional ambiguity.
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
1AAAAA/RMR 1BBBBB/BMR
CHNT
1AAAAA/RMR 1CCCCC/CMR
1BBBBB/BMR 1DDDDD/DMR
SJ326F15FEB CGKSIN HK2
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert len(msg.name_changes) == 2
    assert (msg.name_changes[0].old.raw, msg.name_changes[0].new.raw) == (
        "1AAAAA/RMR", "1CCCCC/CMR",
    )
    assert (msg.name_changes[1].old.raw, msg.name_changes[1].new.raw) == (
        "1BBBBB/BMR", "1DDDDD/DMR",
    )

    # passengers shows the OLD names
    assert len(msg.passengers) == 2
    surnames = {p.surname for p in msg.passengers}
    assert surnames == {"AAAAA", "BBBBB"}

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
    assert msg.name_changes == []
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
1AAAAA/RMR 1BBBBB/SMR
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert msg.name_changes[0].old.raw == "1AAAAA/RMR"
    assert msg.name_changes[0].new.raw == "1BBBBB/SMR"