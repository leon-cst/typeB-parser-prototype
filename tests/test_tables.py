"""
Step 1 tests: confirm every reference table loads and validates cleanly,
and spot-check the lookups the rest of the parser will depend on.

Run with:
    pytest tests/test_tables.py -v
"""
from typeb.tables import loader


def test_all_tables_load_without_error():
    tables = loader.load_all()
    assert set(tables) == {
        "message_identifiers",
        "segment_status_codes",
        "avn_status_codes",
        "error_codes",
        "aux_service_codes",
        "osi_contact_codes",
        "payment_type_codes",
        "office_function_codes",
        "name_title_codes",
    }
    for name, table in tables.items():
        assert len(table) > 0, f"{name} loaded empty"


def test_message_identifiers_contains_expected_codes():
    identifiers = loader.message_identifiers()
    assert "AVN" in identifiers
    assert "RVR" in identifiers
    assert "BOOKING" in identifiers  # synthetic pseudo-identifier
    assert len(identifiers) > 40  # spec table has ~60 across 9 categories


def test_supported_flags_match_current_scope():
    # Current scope per typeb_parser_handoff.md: AVN, RVR, booking-hold,
    # DVD (divide PNR).
    assert loader.is_supported_message_identifier("AVN")
    assert loader.is_supported_message_identifier("RVR")
    assert loader.is_supported_message_identifier("BOOKING")
    assert loader.is_supported_message_identifier("DVD")
    # Everything else should be loaded but NOT marked supported yet.
    assert not loader.is_supported_message_identifier("TLR")
    assert not loader.is_supported_message_identifier("AVS")


def test_unknown_identifier_lookup_is_none_not_an_error():
    assert loader.get_message_identifier("ZZZ") is None
    assert loader.is_known_message_identifier("ZZZ") is False


def test_segment_status_codes_load_and_are_unique_per_file():
    codes = loader.segment_status_codes()
    assert len(codes) > 20
    assert codes["HK"].description == "Holding, confirmed"
    assert codes["NN"].category == "booking_action"


def test_cross_table_ambiguities_are_documented_not_silently_dropped():
    # These are real duplicate/overloaded codes found while transcribing
    # the spec (see loader.py docstring). If someone removes the
    # source_note during a future edit, this test should catch it.
    pn = loader.segment_status_codes()["PN"]
    assert pn.meta and "source_note" in pn.meta

    un_error = loader.error_codes()["UN"]
    assert un_error.meta and "source_note" in un_error.meta

    ll_avn = loader.avn_status_codes()["LL"]
    assert ll_avn.meta and "source_note" in ll_avn.meta


def test_numeric_availability_pattern_matching():
    a5 = loader.match_numeric_availability_code("A5")
    assert a5 == {"prefix": "A", "seats_available": 5, "category": "numeric_availability"}

    l0 = loader.match_numeric_availability_code("L0")
    assert l0["seats_available"] == 0
    assert l0["category"] == "numeric_availability_request_only"

    # Not a numeric-availability code -- should not match.
    assert loader.match_numeric_availability_code("CR") is None
    assert loader.match_numeric_availability_code("A99") is None
    assert loader.match_numeric_availability_code("XX") is None


def test_osi_contact_and_payment_and_aux_tables_load():
    assert loader.osi_contact_codes()["E"].description == "Email"
    assert "CC" in loader.payment_type_codes()
    assert "HTL" in loader.aux_service_codes()


def test_office_function_codes_load():
    codes = loader.office_function_codes()
    assert codes["RM"].description == "Passenger reservation (or bilateral agreement)"
    assert "RI" in codes
    assert "RP" in codes


def test_identifier_has_record_locator_known_values():
    # Availability family: verified false across every REQ02 worked example
    assert loader.identifier_has_record_locator("AVN") is False
    assert loader.identifier_has_record_locator("RVR") is False
    assert loader.identifier_has_record_locator("AVS") is False
    # PNR-bearing types: verified true against REQ03 worked examples
    assert loader.identifier_has_record_locator("DVD") is True
    assert loader.identifier_has_record_locator("BPR") is True
    # Implicit booking: always true, no identifier line present
    assert loader.identifier_has_record_locator("BOOKING") is True


def test_identifier_has_record_locator_unknown_returns_none_not_a_guess():
    # No verified worked example yet for these -- must be None, not a
    # silently assumed True or False.
    assert loader.identifier_has_record_locator("MED") is None
    assert loader.identifier_has_record_locator("PNL") is None