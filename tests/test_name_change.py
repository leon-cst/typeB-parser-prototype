"""
End-to-end CHNT (name change) tests, REQ03 sections 25/30 as
clarified by Parka:
  - single passenger: before/after each a single name (original spec
    example shape)
  - multiple passengers: the full list is rewritten after CHNT, same
    order; only entries that actually change look different
  - a group or named entry may split into multiple entries after CHNT
  - entries with number_in_party < 9 require a title; >= 9 doesn't
    (business rule -- see test_elements.py's Rule 4 tests)

msg.passengers displays the OLD name for a plain rename's identity
(surname/given_name/title) -- other data (tickets, FOID, DOB) still
resolves normally whether a given SSR/OSI line references the old or
new name. A split has no single old identity, so its resulting
passengers display under their new names (see test_cross_reference.py).

Unit tests for the alignment logic itself (_align_name_changes) live
in test_elements.py.
"""
from typeb.messages.booking import parse_booking_message


def test_simple_name_swap_non_group():
    # AAAAA/RMR -> BBBBB/SMR, original spec example shape. OSI TCP
    # names not re-included, per the original message's own note.
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
    assert len(msg.name_changes) == 1
    assert [n.raw for n in msg.name_changes[0].old] == ["1AAAAA/RMR"]
    assert [n.raw for n in msg.name_changes[0].new] == ["1BBBBB/SMR"]

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
    # DDDDD/MRS -> YYYYY/MRS. REQ03 section 25 p.67: a special service
    # tied to the changed name must be retained, not dropped, unless
    # explicitly cancelled.
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
    assert [n.raw for n in msg.name_changes[0].old] == ["1DDDDD/MRS"]
    assert [n.raw for n in msg.name_changes[0].new] == ["1YYYYY/MRS"]

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
1YYYYY/MRS
MZ352Y20MAY ORDBRU HK1
SSR TKNE MZ ORDBRU0352Y20MAY-1YYYYY/MRS.2051234567890C1
NNNN"""

    msg = parse_booking_message(raw)

    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "DDDDD"
    assert msg.passengers[0].ticket_numbers[0].ticket_number == "2051234567890C1"
    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_multi_passenger_rewrite_only_changed_entry_reported():
    # The full list is rewritten after CHNT -- DDDDD/DMR is unchanged
    # and stays that way; only AAAAA/AMR -> ZZZZZ/ZMR is a change.
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
1DDDDD/DMR 1AAAAA/AMR
CHNT
1DDDDD/DMR 1ZZZZZ/ZMR
SJ326F15FEB CGKSIN HK2
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert len(msg.name_changes) == 1
    assert [n.raw for n in msg.name_changes[0].old] == ["1AAAAA/AMR"]
    assert [n.raw for n in msg.name_changes[0].new] == ["1ZZZZZ/ZMR"]

    surnames = {p.surname for p in msg.passengers}
    assert surnames == {"DDDDD", "AAAAA"}  # AAAAA is the old (displayed) name
    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_two_passengers_both_renamed_no_shared_anchor():
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
1AAAAA/RMR 1BBBBB/BMR
CHNT
1CCCCC/CMR 1DDDDD/DMR
SJ326F15FEB CGKSIN HK2
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert len(msg.name_changes) == 2

    surnames = {p.surname for p in msg.passengers}
    assert surnames == {"AAAAA", "BBBBB"}
    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_named_pair_splits_into_two_individuals():
    # "2MILLER/DMR/GMR" -> "1MILLER/DMR 1GREEN/GMR": a shared-surname
    # pair splitting into two separately-named passengers.
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
2MILLER/DMR/GMR
CHNT
1MILLER/DMR 1GREEN/GMR
SJ326F15FEB CGKSIN HK2
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert len(msg.name_changes) == 1
    assert [n.raw for n in msg.name_changes[0].old] == ["2MILLER/DMR/GMR"]
    assert [n.raw for n in msg.name_changes[0].new] == ["1MILLER/DMR", "1GREEN/GMR"]

    # a split displays under the NEW names (no single old identity)
    surnames = {p.surname for p in msg.passengers}
    assert surnames == {"MILLER", "GREEN"}
    assert msg.warnings == []
    assert msg.unrecognized_lines == []


def test_group_splits_into_two_smaller_groups():
    # "30MILLER" -> "15MILLER 15GREEN": both >=9, so neither needs a
    # title (business rule).
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
30MILLER
CHNT
15MILLER 15GREEN
SJ326F15FEB CGKSIN HK30
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [n.raw for n in msg.name_changes[0].old] == ["30MILLER"]
    assert [n.raw for n in msg.name_changes[0].new] == ["15MILLER", "15GREEN"]
    # both are group placeholders -- no individual passenger records
    assert msg.passengers == []
    assert msg.warnings == []


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
1BBBBB/SMR
NNNN"""

    msg = parse_booking_message(raw)

    assert msg.is_name_change is True
    assert [n.raw for n in msg.name_changes[0].old] == ["1AAAAA/RMR"]
    assert [n.raw for n in msg.name_changes[0].new] == ["1BBBBB/SMR"]


def test_multi_person_rename_alongside_unrelated_passenger():
    # Regression: two people sharing a surname both renamed within one
    # multi-person entry, alongside an unrelated unchanged passenger --
    # a prior bug collapsed both renamed people onto one identity.
    raw = """\
QU CGKRMSJ
.SINRM1B 102025
SIN1B 318A15FEB
2KUSUMA/BUDIMR/FREDYMR 1FERNANDO/LEONARDOMR
CHNT
2ANGGARA/KEVINMR/DARRENMR 1FERNANDO/LEONARDOMR
SJ326F15FEB CGKSIN HK3
NNNN"""

    msg = parse_booking_message(raw)

    assert len(msg.passengers) == 3
    given_names = sorted(p.given_name for p in msg.passengers if p.surname == "KUSUMA")
    assert given_names == ["BUDI", "FREDY"]
    assert msg.warnings == []
    assert msg.unrecognized_lines == []