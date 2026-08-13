"""
Cross-reference layer tests. The "full pipeline" tests use only lines
confirmed to parse from the real coworker message -- the two adult+
infant NAME lines were flagged as out-of-spec and don't parse at all
(see test_elements.py::test_name_wrong_token_count_raises_rather_than_guessing),
so they're not part of any end-to-end test here. Building a fabricated
resolution for that open question would defeat the point of raising on
ambiguity in the first place.
"""
import pytest

from typeb.elements.cross_reference import (
    CrossReferenceError,
    cross_reference_passengers,
    validate_party_size,
)
from typeb.elements.name import parse_name_element
from typeb.elements.osi import parse_osi_line
from typeb.elements.ssr import parse_ssr_line


def test_single_passenger_email_dob_foid_all_merge():
    names = [parse_name_element("1KUSUMA/BUDISANTOSOMR")]
    contacts = [
        parse_osi_line("OSI 8G 1KUSUMA/BUDISANTOSOMR E/BUDI.S@GMAIL.COM"),
        parse_osi_line("OSI 8G 1KUSUMA/BUDISANTOSOMR DOB/10MAY85"),
        parse_ssr_line("SSR FOID 8G HK1/8472910483756291-1KUSUMA/BUDISANTOSOMR"),
    ]
    passengers = cross_reference_passengers(names, contacts)

    assert len(passengers) == 1
    p = passengers[0]
    assert p.surname == "KUSUMA"
    assert p.given_name == "BUDISANTOSO"
    assert p.title == "MR"
    assert p.passenger_type == "ADT"  # no CHD/INF signal -- default
    assert p.email == "BUDI.S@GMAIL.COM"
    assert p.date_of_birth_raw == "10MAY85"
    assert p.foid == "8472910483756291"


def test_real_message_subset_two_children_full_pipeline():
    # Every line here is verbatim from the real coworker message and is
    # individually confirmed to parse on its own already -- this test
    # proves they also correctly combine.
    names = [
        parse_name_element("1PRATAMA/ARIELUCY/MSTR"),
        parse_name_element("1PUTRA/KEVINANGGARA/MSTR"),
    ]
    contacts = [
        parse_osi_line("OSI 8G 1 CHD 1PRATAMA/ARIELUCY/MSTR"),
        parse_osi_line("OSI 8G 1 CHD 1PUTRA/KEVINANGGARA/MSTR"),
        parse_osi_line("OSI 8G 1PRATAMA/ARIELUCY/MSTR E/ARIE.L@GMAIL.COM"),
        parse_osi_line("OSI 8G 1PUTRA/KEVINANGGARA/MSTR E/KEVIN.A@GMAIL.COM"),
        parse_osi_line("OSI 8G 1PRATAMA/ARIELUCY/MSTR DOB/15JUN20"),
        parse_osi_line("OSI 8G 1PUTRA/KEVINANGGARA/MSTR DOB/16JUN21"),
        parse_ssr_line("SSR FOID 8G HK1/5102938475610293-1PRATAMA/ARIELUCY/MSTR"),
        parse_ssr_line("SSR FOID 8G HK1/7283940516273849-1PUTRA/KEVINANGGARA/MSTR"),
    ]

    passengers = cross_reference_passengers(names, contacts)

    assert len(passengers) == 2
    by_surname = {p.surname: p for p in passengers}

    pratama = by_surname["PRATAMA"]
    assert pratama.given_name == "ARIELUCY"
    assert pratama.passenger_type == "CHD"
    assert pratama.email == "ARIE.L@GMAIL.COM"
    assert pratama.date_of_birth_raw == "15JUN20"
    assert pratama.foid == "5102938475610293"

    putra = by_surname["PUTRA"]
    assert putra.passenger_type == "CHD"
    assert putra.foid == "7283940516273849"


def test_infant_flag_via_ssr_inft():
    names = [parse_name_element("1ANGGARA/BAYIBUDIMR")]
    contacts = [parse_ssr_line("SSR INFT 8G 1ANGGARA/BAYIBUDIMR")]

    passengers = cross_reference_passengers(names, contacts)
    assert passengers[0].passenger_type == "INF"


def test_seat_modifier_propagates_from_name_element():
    # REQ03 p.11 DOOLEY/EXST example
    names = [parse_name_element("2DOOLEY/ALBERTMR/EXST")]
    contacts = [parse_ssr_line("SSR FOID UA HK1/PP9999999-1DOOLEY/ALBERTMR")]

    passengers = cross_reference_passengers(names, contacts)
    assert len(passengers) == 1  # EXST's phantom seat is not a passenger
    assert passengers[0].seat_modifiers == ["EXST"]


def test_conflicting_passenger_type_signals_raise():
    names = [parse_name_element("1PRATAMA/ARIELUCY/MSTR")]
    contacts = [
        parse_osi_line("OSI 8G 1 CHD 1PRATAMA/ARIELUCY/MSTR"),
        parse_ssr_line("SSR INFT 8G 1PRATAMA/ARIELUCY/MSTR"),  # contradicts CHD above
    ]
    with pytest.raises(CrossReferenceError, match="Conflicting passenger-type signals"):
        cross_reference_passengers(names, contacts)


def test_repeated_identical_type_signal_does_not_raise():
    # Two lines both saying CHD for the same person is not a conflict.
    names = [parse_name_element("1PRATAMA/ARIELUCY/MSTR")]
    contacts = [
        parse_osi_line("OSI 8G 1 CHD 1PRATAMA/ARIELUCY/MSTR"),
        parse_ssr_line("SSR CHLD 8G 1PRATAMA/ARIELUCY/MSTR"),
    ]
    passengers = cross_reference_passengers(names, contacts)
    assert passengers[0].passenger_type == "CHD"


def test_unmatched_reference_raises():
    names = [parse_name_element("1PRATAMA/ARIELUCY/MSTR")]
    contacts = [parse_osi_line("OSI 8G 1SMITH/JOHNMR E/JOHN@GMAIL.COM")]
    with pytest.raises(CrossReferenceError, match="references a passenger not found"):
        cross_reference_passengers(names, contacts)


def test_duplicate_passenger_key_raises():
    # Two NAME elements that happen to describe the exact same
    # (surname, given_name, title) -- can't be disambiguated later.
    names = [
        parse_name_element("1PRATAMA/ARIELUCY/MSTR"),
        parse_name_element("1PRATAMA/ARIELUCY/MSTR"),
    ]
    with pytest.raises(CrossReferenceError, match="resolve to the same"):
        cross_reference_passengers(names, [])


def test_ssr_foid_with_no_name_is_skipped_not_an_error():
    names = [parse_name_element("1RED/PETER")]
    contacts = [
        parse_ssr_line("SSR FOID KL HK1/PP1234567"),  # no name attached
    ]
    # Should not raise -- an unlinked FOID is valid, just doesn't attach.
    passengers = cross_reference_passengers(names, contacts)
    assert passengers[0].foid is None


def test_group_placeholder_contributes_no_passengers():
    names = [parse_name_element("6SEAMEN"), parse_name_element("1RED/PETER")]
    passengers = cross_reference_passengers(names, [])
    assert len(passengers) == 1
    assert passengers[0].surname == "RED"


def test_automated_ssr_referencing_a_name_does_not_crash():
    # Regression: VGML (an AutomatedSsrElement) with a name reference
    # used to raise CrossReferenceError -- it has no case in
    # _apply_element and shouldn't, since the referenced passenger may
    # be one being cancelled/replaced in the same message (name-change
    # messages routinely do this).
    names = [parse_name_element("1DDDDD/MRS")]
    contacts = [
        parse_ssr_line("SSR VGML MZ XX1 ORDBRU0352Y20MAY-1DDDDD/MRS"),
    ]
    passengers = cross_reference_passengers(names, contacts)
    assert len(passengers) == 1
    assert passengers[0].surname == "DDDDD"


def test_automated_ssr_referencing_an_absent_name_does_not_crash():
    # The referenced passenger doesn't even need to exist in this call's
    # name_elements -- e.g. a name-change message where the SSR still
    # names the passenger being replaced.
    names = [parse_name_element("1YYYYY/MRS")]
    contacts = [
        parse_ssr_line("SSR VGML MZ XX1 ORDBRU0352Y20MAY-1DDDDD/MRS"),
    ]
    passengers = cross_reference_passengers(names, contacts)
    assert len(passengers) == 1
    assert passengers[0].surname == "YYYYY"


# --------------------------------------------------------------------------
# validate_party_size
# --------------------------------------------------------------------------

def test_validate_party_size_matching_returns_no_warnings():
    names = [parse_name_element("2FORD/E/B")]
    warnings = validate_party_size(names, segment_number_in_party=2)
    assert warnings == []


def test_validate_party_size_mismatch_returns_warning_not_error():
    names = [parse_name_element("2FORD/E/B")]
    warnings = validate_party_size(names, segment_number_in_party=1)
    assert len(warnings) == 1
    assert "total party size of 2" in warnings[0]
    assert "requests 1 seat" in warnings[0]


def test_group_placeholder_contributes_to_party_size():
    names = [parse_name_element("6SEAMEN")]
    # 6SEAMEN legitimately represents 6 seats -- matches a 6-seat segment
    assert validate_party_size(names, segment_number_in_party=6) == []