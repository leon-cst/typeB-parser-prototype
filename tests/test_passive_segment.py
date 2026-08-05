"""
REQ03 section 17-18 (passive segment / advice of electronic ticket
number). All five CONTOH examples transcribed verbatim, except:
  - CONTOH-4's source lists 20 pax via Indonesian prose ("dan seterusnya
    sampai 19 pax"); that prose is the document explaining the example,
    not transmitted content, so the party is written out as the 5 named
    pax the example actually shows and the segment counts adjusted to
    match.
"""
import pytest

from typeb.elements.errors import ElementParseError
from typeb.elements.name import parse_name_element, parse_name_line
from typeb.elements.osi import parse_osi_line
from typeb.elements.ssr import parse_ssr_line
from typeb.messages.booking import parse_booking_message
from typeb.model.envelope import RecordLocator


# --------------------------------------------------------------------------
# NAME -- glued title on every token, not just the last
# --------------------------------------------------------------------------

def test_name_glued_title_on_every_token():
    n = parse_name_element("2AAAAA/JXXMR/ZYYYMR")
    assert [(p.given_name, p.title) for p in n.people] == [("JXX", "MR"), ("ZYYY", "MR")]


def test_name_glued_title_short_given_names():
    n = parse_name_element("2AAAAA/TMR/BBMR")
    assert [(p.given_name, p.title) for p in n.people] == [("T", "MR"), ("BB", "MR")]


def test_name_no_title_group_still_unaffected():
    n = parse_name_element("3FORD/E/B/C")
    assert [(p.given_name, p.title) for p in n.people] == [
        ("E", None), ("B", None), ("C", None)
    ]


# --------------------------------------------------------------------------
# NAME -- several groups on one line (REQ03 p.10)
# --------------------------------------------------------------------------

def test_name_line_with_several_groups():
    elements = parse_name_line("1AAAAA/AMR 1BBBBB/BMR 1CCCCC/CMR")
    assert [e.surname for e in elements] == ["AAAAA", "BBBBB", "CCCCC"]
    assert all(e.number_in_party == 1 for e in elements)


def test_name_line_single_group_returns_one_element():
    assert len(parse_name_line("1RAHARJO/BAMBANGMR")) == 1


def test_name_line_group_without_leading_count_raises():
    with pytest.raises(ElementParseError, match="does not begin a name group"):
        parse_name_line("1AAAAA/AMR DDDDD/DMR")


# --------------------------------------------------------------------------
# Record locator -- user_type omitted without a placeholder slash
# --------------------------------------------------------------------------

def test_record_locator_valid_user_type_fills_positionally():
    rl = RecordLocator.parse("HDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY")
    assert rl.user_type == "T"
    assert rl.iso_country_code == "JP"
    assert rl.iso_currency_code == "JPY"


def test_record_locator_invalid_user_type_shifts_remaining_fields():
    rl = RecordLocator.parse("NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU")
    assert rl.user_type is None
    assert rl.iso_country_code == "NL"
    assert rl.iso_currency_code == "CHF"
    assert rl.duty_code == "SU"


def test_record_locator_trailing_empty_slashes_unaffected():
    rl = RecordLocator.parse("HDR1B CPNR1B/MADIB0500/1234567/////")
    assert rl.travel_agent_city_code == "MADIB0500"
    assert rl.iata_number == "1234567"
    assert rl.user_type is None


# --------------------------------------------------------------------------
# SSR TKNE -- every shape the spec's own examples use
# --------------------------------------------------------------------------

def test_ssr_tkne_glued_segment_reference():
    s = parse_ssr_line("SSR TKNE NH HK1 NRTLAX0123Y21DEC.2051234567890C1")
    assert s.airline_code == "NH"
    assert s.action_code == "HK"
    assert s.number_in_party == 1
    assert s.segment_reference_raw == "NRTLAX0123Y21DEC"
    assert s.name is None
    assert s.ticket_number_raw == "2051234567890C1"


def test_ssr_tkne_without_action_code():
    s = parse_ssr_line("SSR TKNE NH NRTLAX 0006Y21DEC-1AAAAA/JXXMR.2051234567890C1")
    assert s.action_code is None
    assert s.number_in_party is None
    assert s.segment_reference_raw == "NRTLAX 0006Y21DEC"
    assert s.name.surname == "AAAAA"
    assert s.name.given_name == "JXX"


def test_ssr_tkne_fully_spaced_segment_reference():
    # REQ03's own interline example, spaced further than the section 18 ones
    s = parse_ssr_line("SSR TKNE AA HK1 DFWMIA 0614 Y 15AUG-1BBBBB/TMR.0061234567812C2")
    assert s.segment_reference_raw == "DFWMIA 0614 Y 15AUG"
    assert s.ticket_number_raw == "0061234567812C2"


def test_ssr_tkne_missing_dot_separator_raises():
    with pytest.raises(ElementParseError, match="missing the '.'"):
        parse_ssr_line("SSR TKNE NH HK1 NRTLAX0123Y21DEC")


# --------------------------------------------------------------------------
# SSR RLOC / GRPS, OSI RLOC
# --------------------------------------------------------------------------

def test_ssr_rloc():
    s = parse_ssr_line("SSR RLOC NH NRTORD0012T21DEC.CPNRNH")
    assert s.airline_code == "NH"
    assert s.segment_reference_raw == "NRTORD0012T21DEC"
    assert s.record_locator == "CPNRNH"


def test_ssr_grps_has_no_action_code_or_count():
    s = parse_ssr_line("SSR GRPS NH TSP20 BALITOURS")
    assert s.airline_code == "NH"
    assert s.structured_text == "TSP20"
    assert s.group_name == "BALITOURS"


def test_osi_rloc():
    o = parse_osi_line("OSI NH RLOC NH CPNRNH")
    assert o.airline_code == "NH"
    assert o.record_locator_airline == "NH"
    assert o.record_locator == "CPNRNH"


# --------------------------------------------------------------------------
# Full messages
# --------------------------------------------------------------------------

def test_contoh_1_pk_segment_ticket_no_name_reference():
    raw = """\
QU TYORMNH
.HDQRM1F 241310
HDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY
1AAAAA/TCCCMR
MH123Y21DEC NRTLAX PK1/1705 0945
SSR TKNE NH HK1 NRTLAX0123Y21DEC.2051234567890C1"""
    msg = parse_booking_message(raw)
    assert len(msg.passengers) == 1
    assert msg.passengers[0].given_name == "TCCC"
    assert msg.segments[0].action_code == "PK"
    assert msg.unrecognized_lines == []


def test_contoh_2_pl_segment_two_tickets_and_osi_rloc():
    raw = """\
QU TYORMNH
.HDQRM1F 132014
HDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY
2AAAAA/JXXMR/ZYYMR
NH006Y21DEC NRTLAX PL2/1705 0945
SSR TKNE NH NRTLAX 0006Y21DEC-1AAAAA/JXXMR.2051234567890C1
SSR TKNE NH NRTLAX 0006Y21DEC-1AAAAA/ZYYMR.2051234567891C1
OSI NH RLOC NH CPNRNH"""
    msg = parse_booking_message(raw)
    assert msg.segments[0].action_code == "PL"
    by_given = {p.given_name: p for p in msg.passengers}
    assert by_given["JXX"].ticket_numbers == ["2051234567890C1"]
    assert by_given["ZYY"].ticket_numbers == ["2051234567891C1"]
    assert msg.airline_record_locators == ["CPNRNH"]
    assert msg.unrecognized_lines == []


def test_contoh_3_pk_segment_spaced_segment_reference():
    raw = """\
QU TYORMNH
.HDQRM1F 251014
HDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY
1NNNNN/TBBBBMR
NH006Y21DEC NRTLAX PK1/1705 0945
SSR TKNE NH HK1 NRTLAX 0006Y21DEC.2051234567890C1"""
    msg = parse_booking_message(raw)
    assert msg.passengers[0].surname == "NNNNN"
    assert msg.unrecognized_lines == []


def test_contoh_4_group_pu_segments_multi_group_name_line():
    raw = """\
QU TYORMNH
.HDQRM1F 232120
HDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY
1AAAAA/AMR 1BBBBB/BMR 1CCCCC/CMR 1DDDDD/DMR
1ZZZZZ/ZMR
NH012T21DEC NRTORD PU5
NH011T28DEC ORDNRT PU5
SSR GRPS NH TSP20 BALITOURS
SSR TKNE NH HK1 NRTORD0002T21DEC-1ZZZZZ/ZMR.2051234567890C1
SSR TKNE NH HK1 ORDNRT0002T28DEC-1ZZZZZ/ZMR.2051234567891C2
SSR RLOC NH NRTORD0012T21DEC.CPNRNH"""
    msg = parse_booking_message(raw)
    assert len(msg.passengers) == 5
    assert [s.action_code for s in msg.segments] == ["PU", "PU"]
    added = next(p for p in msg.passengers if p.surname == "ZZZZZ")
    assert added.ticket_numbers == ["2051234567890C1", "2051234567891C2"]
    assert msg.airline_record_locators == ["CPNRNH"]
    assert msg.unrecognized_lines == []


def test_contoh_5_pu_segment_ticket_after_initial_transmission():
    raw = """\
QU TYORMNH
.HDQRM1F 101523
HDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY
2AAAAA/TMR/BBMR
NH006Y21DEC NRTLAX PU2
SSR TKNE NH HK1 NRTLAX 0006Y21DEC-1AAAAA/TMR.2051234567890C1"""
    msg = parse_booking_message(raw)
    assert msg.segments[0].action_code == "PU"
    by_given = {p.given_name: p for p in msg.passengers}
    assert by_given["T"].ticket_numbers == ["2051234567890C1"]
    assert by_given["BB"].ticket_numbers == []
    assert msg.unrecognized_lines == []