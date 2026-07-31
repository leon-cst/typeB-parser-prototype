"""Tests for the AVN and RVR orchestrators."""
import pytest

from typeb.elements.errors import ElementParseError
from typeb.messages.avn import parse_availability_message
from typeb.messages.rvr import parse_recap_message


def test_avn_message_real_example():
    raw = """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
AA800 J 01JUN CGKDPS
NNNN"""
    msg = parse_availability_message(raw)
    assert msg.envelope.message_identifier == "AVN"
    assert len(msg.availability_lines) == 2
    assert msg.availability_lines[0].airline_code == "AA"
    assert msg.unrecognized_lines == []


def test_avn_unknown_line_collected_not_fatal():
    raw = """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
GARBAGE LINE HERE
NNNN"""
    msg = parse_availability_message(raw)
    assert len(msg.availability_lines) == 1
    assert len(msg.unrecognized_lines) == 1
    assert msg.unrecognized_lines[0].tokenizer_kind == "UNKNOWN"


def test_avn_booking_content_hard_fails():
    raw = """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
1RAHARJO/BAMBANGMR
NNNN"""
    with pytest.raises(ElementParseError, match="Unexpected NAME shape"):
        parse_availability_message(raw)


def test_avn_called_on_non_avn_message_raises():
    raw = """\
QU HDQRI8G
.JKTRM1G 161102
RVR
8G407/16JUN26-30DEC26/1234567
NNNN"""
    with pytest.raises(ElementParseError, match="non-AVN message"):
        parse_availability_message(raw)


def test_rvr_message_real_example():
    raw = """\
QU HDQRI8G
.JKTRM1G 161102
RVR
8G407/16JUN26-30DEC26/1234567
NNNN"""
    msg = parse_recap_message(raw)
    assert msg.envelope.message_identifier == "RVR"
    assert len(msg.recap_lines) == 1
    assert msg.recap_lines[0].date_range_raw == "16JUN26-30DEC26"
    assert msg.unrecognized_lines == []


def test_rvr_message_single_date_shape():
    # REQ02 p.14 -- the shape that was originally broken end-to-end
    # (misclassified as UNKNOWN by the tokenizer) before this fix.
    raw = """\
QU SINRM8G
.SINRMGDS 311024
RVR
8G191/31JUL26 DILDPS
NNNN"""
    msg = parse_recap_message(raw)
    assert len(msg.recap_lines) == 1
    assert msg.recap_lines[0].date_raw == "31JUL26"
    assert msg.recap_lines[0].route == "DILDPS"
    assert msg.unrecognized_lines == []


def test_rvr_message_single_date_no_route_means_all():
    raw = """\
QU JKTRM8G
.AMSRM1G 121025
RVR
8G123/16JUN26
NNNN"""
    msg = parse_recap_message(raw)
    assert msg.recap_lines[0].route == "ALL"


def test_rvr_avn_content_hard_fails():
    raw = """\
QU HDQRI8G
.JKTRM1G 161102
RVR
AA800 F 01JUN CGKDPS
NNNN"""
    with pytest.raises(ElementParseError, match="Unexpected AVAILABILITY_LINE shape"):
        parse_recap_message(raw)


def test_rvr_called_on_non_rvr_message_raises():
    raw = """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
NNNN"""
    with pytest.raises(ElementParseError, match="non-RVR message"):
        parse_recap_message(raw)