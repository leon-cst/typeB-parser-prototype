"""
SSR element parser tests. FOID tests come from REQ03's own official
field table plus a real message. INFT/CHLD tests come only from the real
message, since REQ03 section 9 names these codes but gives no worked
format example for either.
"""
import pytest

from typeb.elements.errors import ElementParseError
from typeb.elements.ssr import parse_ssr_line


def test_ssr_foid_from_real_message():
    ssr = parse_ssr_line("SSR FOID 8G HK1/8472910483756291-2KUSUMA/BUDISANTOSO/MR")
    assert ssr.airline_code == "8G"
    assert ssr.action_code == "HK"
    assert ssr.number_in_party == 1
    assert ssr.structured_text == "8472910483756291"
    assert ssr.name is not None
    assert ssr.name.surname == "KUSUMA"
    assert ssr.name.given_name == "BUDISANTOSO"
    assert ssr.name.title == "MR"


def test_ssr_foid_from_spec_example():
    # REQ03 p.20 non-automated example 1
    ssr = parse_ssr_line("SSR FOID KL HK1/PP1234567-1RED/PETER")
    assert ssr.airline_code == "KL"
    assert ssr.action_code == "HK"
    assert ssr.number_in_party == 1
    assert ssr.structured_text == "PP1234567"
    assert ssr.name.surname == "RED"
    assert ssr.name.given_name == "PETER"


def test_ssr_foid_without_name_is_valid():
    ssr = parse_ssr_line("SSR FOID KL HK1/PP1234567")
    assert ssr.structured_text == "PP1234567"
    assert ssr.name is None


def test_ssr_inft_from_real_message():
    ssr = parse_ssr_line("SSR INFT 8G 1ANGGARA/BAYIBUDI/MR")
    assert ssr.ssr_code == "INFT"
    assert ssr.airline_code == "8G"
    assert ssr.name.surname == "ANGGARA"
    assert ssr.name.given_name == "BAYIBUDI"
    assert ssr.name.title == "MR"


def test_ssr_chld_uses_same_shape_as_inft():
    ssr = parse_ssr_line("SSR CHLD 8G 1PRATAMA/ARIELUCY/MSTR")
    assert ssr.ssr_code == "CHLD"
    assert ssr.name.surname == "PRATAMA"


def test_ssr_codeless_email_from_real_message():
    # Confirmed real: SSR can carry email with NO 4-letter code at all.
    ssr = parse_ssr_line("SSR 8G 1ANGGARA/BAYIBUDI/MR E/BAYI1@GMAIL.COM")
    assert ssr.source == "SSR"
    assert ssr.airline_code == "8G"
    assert ssr.name.surname == "ANGGARA"
    assert ssr.name.given_name == "BAYIBUDI"
    assert ssr.email == "BAYI1@GMAIL.COM"


def test_ssr_codeless_dob_shape_also_valid():
    # Same code-less shape confirmed for DOB, not just email.
    ssr = parse_ssr_line("SSR 8G 1ANGGARA/BAYIBUDI/MR DOB/30SEP25")
    assert ssr.source == "SSR"
    assert ssr.date_of_birth_raw == "30SEP25"


def test_ssr_and_osi_email_share_identical_parsing_except_source():
    # Same content, different keyword -- only `source` should differ.
    ssr = parse_ssr_line("SSR 8G 1ANGGARA/BAYIBUDI/MR E/BAYI1@GMAIL.COM")
    from typeb.elements.osi import parse_osi_line
    osi = parse_osi_line("OSI 8G 1ANGGARA/BAYIBUDI/MR E/BAYI1@GMAIL.COM")

    assert ssr.source == "SSR"
    assert osi.source == "OSI"
    assert ssr.airline_code == osi.airline_code
    assert ssr.email == osi.email
    assert ssr.name == osi.name


def test_ssr_inft_wrong_token_count_raises():
    with pytest.raises(ElementParseError, match="expected exactly 4 tokens"):
        parse_ssr_line("SSR INFT 8G EXTRA 1ANGGARA/BAYIBUDI/MR")


def test_ssr_unimplemented_code_raises_clearly():
    with pytest.raises(ElementParseError, match="No parser implemented yet for SSR code 'NSST'"):
        parse_ssr_line("SSR NSST LH NN1 FRAMXP17452 0NOV-1SCHULTZ/LEO")


def test_ssr_foid_leading_digit_not_mistaken_for_party_count():
    # Regression case: the name-reference's leading "2" here is NOT "2
    # people follow" (as it would mean on a real NAME line) -- it's
    # carried over from BUDISANTOSO's own original party size elsewhere
    # in the message. An earlier version of this parser reused
    # parse_name_element here and wrongly split this into two people.
    ssr = parse_ssr_line("SSR FOID 8G HK1/8472910483756291-2KUSUMA/BUDISANTOSO/MR")
    assert ssr.name.leading_number == 2
    assert ssr.name.surname == "KUSUMA"
    assert ssr.name.given_name == "BUDISANTOSO"
    assert ssr.name.title == "MR"


def test_not_an_ssr_line_raises():
    with pytest.raises(ElementParseError, match="Not an SSR line"):
        parse_ssr_line("OSI 8G 1BAMBANG/MR E/BUDI@GMAIL.COM")