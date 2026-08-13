"""
OSI element parser tests. Email/DOB shapes and the CHD/INF flag shape are
both confirmed against REQ03's own worked examples (p.22-23) as well as
real message lines.
"""
import pytest

from typeb.elements.errors import ElementParseError
from typeb.elements.osi import parse_osi_line


def test_osi_email_from_spec_example():
    # REQ03 p.23
    osi = parse_osi_line("OSI GA 1BAMBANG/MR E/BABANG@GMAIL.COM")
    assert osi.source == "OSI"
    assert osi.airline_code == "GA"
    assert osi.name.surname == "BAMBANG"
    assert osi.email == "BABANG@GMAIL.COM"


def test_osi_email_from_real_message():
    osi = parse_osi_line("OSI 8G 2KUSUMA/BUDISANTOSO/MR E/BUDI.S@GMAIL.COM")
    assert osi.source == "OSI"
    assert osi.airline_code == "8G"
    assert osi.name.surname == "KUSUMA"
    assert osi.name.given_name == "BUDISANTOSO"
    assert osi.email == "BUDI.S@GMAIL.COM"


def test_osi_dob_from_real_message():
    # Note: real traffic uses 2-digit year, unlike REQ03's own 4-digit
    # example -- kept raw rather than normalized, see DobElement docstring
    osi = parse_osi_line("OSI 8G 2KUSUMA/BUDISANTOSO/MR DOB/10MAY85")
    assert osi.source == "OSI"
    assert osi.airline_code == "8G"
    assert osi.name.surname == "KUSUMA"
    assert osi.date_of_birth_raw == "10MAY85"


def test_osi_child_flag_from_spec_example():
    # REQ03 p.22 official example
    osi = parse_osi_line("OSI YY 1 CHD 1MARSH/E")
    assert osi.airline_code == "YY"
    assert osi.unexplained_field == "1"
    assert osi.passenger_type == "CHD"
    assert osi.name.surname == "MARSH"
    assert osi.name.given_name == "E"


def test_osi_infant_flag_from_spec_example():
    osi = parse_osi_line("OSI YY 1 INF 1POPIV/O")
    assert osi.passenger_type == "INF"
    assert osi.name.surname == "POPIV"


def test_osi_child_flag_from_real_message():
    osi = parse_osi_line("OSI 8G 1 CHD 1PRATAMA/ARIELUCY/MSTR")
    assert osi.airline_code == "8G"
    assert osi.unexplained_field == "1"
    assert osi.passenger_type == "CHD"
    assert osi.name.surname == "PRATAMA"
    assert osi.name.title == "MSTR"


def test_osi_party_count_full_names():
    # REQ03 section 25 Option-1 non-group "who else is booked" list
    osi = parse_osi_line("OSI SJ TCP3 1CCCCC/KMR 1DDDDD/ZMR")
    assert osi.airline_code == "SJ"
    assert osi.total_party_count == 3
    assert [n.surname for n in osi.names] == ["CCCCC", "DDDDD"]


def test_osi_party_count_bare_surname_reference():
    # names may be a partial list, and a name may have no given
    # name/title at all (bare surname, no slash)
    osi = parse_osi_line("OSI YY TCP3 1ALLEN")
    assert osi.total_party_count == 3
    assert len(osi.names) == 1
    assert osi.names[0].surname == "ALLEN"
    assert osi.names[0].given_name is None
    assert osi.names[0].title is None


def test_osi_party_count_no_names():
    osi = parse_osi_line("OSI MZ TCP20")
    assert osi.total_party_count == 20
    assert osi.names == []


def test_osi_unrecognized_shape_raises_clearly():
    with pytest.raises(ElementParseError, match="No parser implemented yet for this OSI shape"):
        parse_osi_line("OSI BA TKNO 1261234567890")


def test_not_an_osi_line_raises():
    with pytest.raises(ElementParseError, match="Not an OSI line"):
        parse_osi_line("SSR FOID 8G HK1/12345-1RED/PETER")