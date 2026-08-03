"""
Tests for parse_booking_message -- the full envelope + tokenizer +
element parsers + cross-reference pipeline, in one call.
"""
import pytest

from typeb.elements.errors import ElementParseError
from typeb.messages.booking import parse_booking_message


def test_clean_single_passenger_booking():
    # REQ03 p.49, verbatim
    raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015"""

    msg = parse_booking_message(raw)

    assert msg.envelope.message_identifier is None
    assert len(msg.envelope.record_locators) == 1
    rl = msg.envelope.record_locators[0]
    assert rl.raw == "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"
    assert rl.booking_office == "NYC1G"
    assert rl.location_of_record == "CPNR1G"

    assert len(msg.passengers) == 1
    p = msg.passengers[0]
    assert p.surname == "RAHARJO"
    assert p.given_name == "BAMBANG"
    assert p.title == "MR"
    assert p.passenger_type == "ADT"

    assert len(msg.segments) == 1
    assert msg.segments[0].airline_code == "8G"

    assert msg.warnings == []  # party size 1 == seat count 1, matches
    assert msg.unrecognized_lines == []


def test_real_message_subset_two_children_end_to_end():
    # Verbatim real lines that individually parse (the packed adult+
    # infant lines are excluded -- see test_cross_reference.py's module
    # docstring for why). Segment line corrected in two ways from the
    # ambiguous original "8G191U30JUL DILDPS SSR4/0910 1015": action
    # code "SSR4" -> "SS4" (see the SSR4-vs-SS4 discussion earlier), and
    # the "/" before the times removed -- every OTHER verified SEGMENT
    # example is space-separated with no slash there, so that slash was
    # a second, separate anomaly I'd conflated with the first one.
    raw = """\
QU CGKRM8G
.SINRMGDS 301436
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1PRATAMA/ARIELUCY/MSTR
1PUTRA/KEVINANGGARA/MSTR
8G191U30JUL DILDPS SS2 0910 1015
OSI 8G 1 CHD 1PRATAMA/ARIELUCY/MSTR
OSI 8G 1 CHD 1PUTRA/KEVINANGGARA/MSTR
OSI 8G 1PRATAMA/ARIELUCY/MSTR E/ARIE.L@GMAIL.COM
OSI 8G 1PUTRA/KEVINANGGARA/MSTR E/KEVIN.A@GMAIL.COM
SSR FOID 8G HK1/5102938475610293-1PRATAMA/ARIELUCY/MSTR
SSR FOID 8G HK1/7283940516273849-1PUTRA/KEVINANGGARA/MSTR
NNNN"""

    msg = parse_booking_message(raw)

    assert len(msg.passengers) == 2
    by_surname = {p.surname: p for p in msg.passengers}
    assert by_surname["PRATAMA"].passenger_type == "CHD"
    assert by_surname["PRATAMA"].email == "ARIE.L@GMAIL.COM"
    assert by_surname["PRATAMA"].foid == "5102938475610293"
    assert by_surname["PUTRA"].passenger_type == "CHD"

    assert len(msg.segments) == 1
    assert msg.segments[0].number_in_party == 2

    assert msg.warnings == []  # 1+1 party size == 2 seats requested
    assert msg.unrecognized_lines == []


def test_unrecognized_ssr_code_collected_not_fatal():
    raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015
SSR NSST 8G NN1 CGKDPS0871Y17AUG"""

    msg = parse_booking_message(raw)

    # The rest of the message still parses.
    assert len(msg.passengers) == 1
    assert len(msg.segments) == 1

    assert len(msg.unrecognized_lines) == 1
    unrec = msg.unrecognized_lines[0]
    assert unrec.tokenizer_kind == "SSR"
    assert "NSST" in unrec.reason
    assert unrec.raw == "SSR NSST 8G NN1 CGKDPS0871Y17AUG"


def test_unknown_line_collected_not_fatal():
    raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015
THIS IS NOT VALID TYPEB AT ALL"""

    msg = parse_booking_message(raw)

    assert len(msg.passengers) == 1
    assert len(msg.unrecognized_lines) == 1
    assert msg.unrecognized_lines[0].tokenizer_kind == "UNKNOWN"
    assert msg.unrecognized_lines[0].raw == "THIS IS NOT VALID TYPEB AT ALL"


def test_malformed_segment_fails_the_whole_message():
    # City pair is 5 characters instead of 6 -- genuine malformation,
    # not merely unimplemented. Must NOT be swallowed into
    # unrecognized_lines the way an UnrecognizedElementError would be.
    raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKD NN1 0910 1015"""

    with pytest.raises(ElementParseError, match="6 characters"):
        parse_booking_message(raw)


def test_distinct_surnames_adult_and_infant_now_parses_through_full_pipeline():
    # This was the original real-world divergent shape that used to hard
    # fail through the full orchestrator. Once Logic B (distinct
    # surnames) was added per explicit instruction, it now correctly
    # resolves into two passengers.
    raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
2KUSUMA/BUDISANTOSO/MR/ANGGARA/BAYIBUDI/MR
8G083F24SEP CGKDPS NN2 0910 1015"""

    msg = parse_booking_message(raw)
    assert len(msg.passengers) == 2
    by_surname = {p.surname: p for p in msg.passengers}
    assert by_surname["KUSUMA"].given_name == "BUDISANTOSO"
    assert by_surname["ANGGARA"].given_name == "BAYIBUDI"
    assert msg.warnings == []  # party size 2 == segment's NN2, matches


def test_party_size_mismatch_produces_warning_not_failure():
    # NAME declares 1 person, SEGMENT requests 2 seats -- REQ03's
    # invariant doesn't hold, but this is a warning per policy (could be
    # legitimate infant-inclusion variance), not a hard failure.
    raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN2 0910 1015"""

    msg = parse_booking_message(raw)

    assert len(msg.warnings) == 1
    assert "total party size of 1" in msg.warnings[0]
    assert "requests 2 seat" in msg.warnings[0]


def test_non_booking_message_raises_clearly():
    raw = """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
NNNN"""

    with pytest.raises(ElementParseError, match="non-booking message"):
        parse_booking_message(raw)