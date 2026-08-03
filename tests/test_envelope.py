"""
Envelope parser tests, built from real worked examples in REQ02/REQ03
rather than synthetic input -- these are the spec's own sample messages,
transcribed. Two of them (test_multi_address_envelope,
test_bpr_double_record_locator) come from pages that print the example in
an annotated teaching format (literal labels like "NAME ----" or
"REC.LOC ----" prefixed to each line for the reader's benefit) -- those
labels are stripped here since they're the document's own exposition, not
part of the transmitted message. That's noted per-fixture below.
"""
import pytest

from typeb.envelope.parser import EnvelopeParseError, parse_envelope
from typeb.model.envelope import RecordLocator


def test_avn_envelope_has_no_record_locator():
    # REQ02 p.7 -- real request example
    raw = """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
AA800 J 01JUN CGKDPS
AA800 Y 01JUN CGKDPS
AA800 B 01JUN CGKDPS
NNNN"""
    envelope, body = parse_envelope(raw)

    assert envelope.priority_code == "QU"
    assert len(envelope.addresses) == 1
    assert envelope.addresses[0].city_code == "FTW"
    assert envelope.addresses[0].office_code == "RM"
    assert envelope.addresses[0].designator == "AA"

    assert envelope.comm_reference.origin.city_code == "HDQ"
    assert envelope.comm_reference.origin.office_code == "RI"
    assert envelope.comm_reference.origin.designator == "8G"
    assert envelope.comm_reference.date_time_raw == "201025"

    assert envelope.message_identifier == "AVN"
    assert envelope.record_locators == []  # availability family: none

    assert body[0] == "AA800 F 01JUN CGKDPS"
    assert body[-1] == "NNNN"


def test_rvr_envelope_has_no_record_locator():
    # REQ03 p.13 -- real request example
    raw = """\
QU HDQRI8G
.JKTRM1G 161102
RVR
8G407/16JUN26-30DEC26/1234567
NNNN"""
    envelope, body = parse_envelope(raw)

    assert envelope.message_identifier == "RVR"
    assert envelope.record_locators == []
    assert body[0] == "8G407/16JUN26-30DEC26/1234567"


def test_booking_envelope_has_implicit_identifier_and_record_locator():
    # REQ03 p.49 -- real booking request example, no message identifier
    # line at all (REQ03 section 5's implicit-booking rule)
    raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015"""
    envelope, body = parse_envelope(raw)

    assert envelope.message_identifier is None
    assert envelope.effective_identifier == "BOOKING"
    assert len(envelope.record_locators) == 1

    rl = envelope.record_locators[0]
    assert rl.raw == "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"
    assert rl.booking_office == "NYC1G"
    assert rl.location_of_record == "CPNR1G"
    # POS fields are filled strictly positionally (field 1 -> field N for
    # however many are present); nothing on the wire marks a field as
    # skipped mid-sequence, so a value can only be "missing" by being
    # absent from the END of the line, not the middle. Here "NL" lands
    # in field 5 (user_type) purely by position, even though it doesn't
    # match the spec's single-letter A/E/N/T user_type values -- that
    # mismatch is a real observation about this message, not something
    # the parser should silently correct by guessing a shift.
    assert rl.travel_agent_city_code == "AAA"
    assert rl.iata_number == "111122223333"
    assert rl.city_airport_code == "NYC"
    assert rl.crs_code == "1G"
    assert rl.user_type == "NL"
    assert rl.iso_country_code == "CHF"
    assert rl.iso_currency_code == "SU"
    assert rl.duty_code is None
    assert rl.user_id_pss is None
    assert rl.point_of_departure is None

    assert body[0] == "1RAHARJO/BAMBANGMR"
    assert body[1] == "8G083F24SEP CGKDPS NN1 0910 1015"


def test_multi_address_envelope():
    # REQ03 p.25-26 ("EACH AIRLINE ADDRESSED WILL ACT ONLY ON ITS OWN
    # SEAT"), with the source page's teaching labels ("REC.LOC", "NAME",
    # "ARRIVAL" printed as line prefixes) stripped -- those are the
    # document explaining the example to the reader, not transmitted
    # content. The two addresses (HDQRMAA, HDQRMUA) and the record
    # locator/date-time digits are kept verbatim from the source.
    raw = """\
QU HDQRMAA HDQRMUA
.CPHRMSK 01601
CPHSK 1713
2BORGE/A/D
SK919F04JUN CPHJFK HK2/1000 1300"""
    envelope, body = parse_envelope(raw)

    assert len(envelope.addresses) == 2
    assert envelope.addresses[0].designator == "AA"
    assert envelope.addresses[1].designator == "UA"

    assert envelope.message_identifier is None
    assert len(envelope.record_locators) == 1
    assert envelope.record_locators[0].raw == "CPHSK 1713"
    assert envelope.record_locators[0].booking_office == "CPHSK"
    assert envelope.record_locators[0].location_of_record == "1713"
    assert body[0] == "2BORGE/A/D"


def test_dvd_envelope_has_identifier_and_single_record_locator():
    # REQ03 p.63 -- real DVD example, clean (no teaching labels)
    raw = """\
QU CGKRMSJ
.HDQRM8G 101234
DVD
HDQ8G CPNRSJ/ABC/12345678/LON/1G/T/GB
1AAAAA/MR
SJ920Y15FEB SINAMS XX1
8G320Y15FEB CGKSIN HK1/1030 1210
SJ890Y15FEB SINLON SS1/1350 1610
OSI YY RLOC HDQ8GCPNRSJ"""
    envelope, body = parse_envelope(raw)

    assert envelope.message_identifier == "DVD"
    assert len(envelope.record_locators) == 1

    rl = envelope.record_locators[0]
    assert rl.raw == "HDQ8G CPNRSJ/ABC/12345678/LON/1G/T/GB"
    assert rl.booking_office == "HDQ8G"
    assert rl.location_of_record == "CPNRSJ"
    assert rl.travel_agent_city_code == "ABC"
    assert rl.iata_number == "12345678"
    assert rl.city_airport_code == "LON"
    assert rl.crs_code == "1G"
    assert rl.user_type == "T"
    assert rl.iso_country_code == "GB"
    assert rl.iso_currency_code is None

    assert body[0] == "1AAAAA/MR"
    assert body[1] == "SJ920Y15FEB SINAMS XX1"


def test_bpr_double_record_locator():
    # REQ03 p.62 -- real BPR example with a primary AND secondary record
    # locator line (REQ03 p.9's "bilateral agreement" primary/secondary
    # rule in practice) before the name element. The primary line's
    # trailing "/////"  is a run of empty POS fields -- still valid,
    # every field just resolves to None.
    raw = """\
QU HDQRMSJ
.HDQRM1B 131210
BPR
HDR1B CPNR1B/MADIB0500/1234567/////
HDQSJ CPNRSJ
1AAAAA/RMR 1BBBBB/KMR 1FFFFF/LMR
SJ340Y30JUL CGKSIN HK3/1145 1515"""
    envelope, body = parse_envelope(raw)

    assert envelope.message_identifier == "BPR"
    assert len(envelope.record_locators) == 2

    primary, secondary = envelope.record_locators
    assert primary.raw == "HDR1B CPNR1B/MADIB0500/1234567/////"
    assert primary.booking_office == "HDR1B"
    assert primary.location_of_record == "CPNR1B"
    assert primary.travel_agent_city_code == "MADIB0500"
    assert primary.iata_number == "1234567"
    assert primary.city_airport_code is None
    assert primary.crs_code is None
    assert primary.user_type is None

    assert secondary.raw == "HDQSJ CPNRSJ"
    assert secondary.booking_office == "HDQSJ"
    assert secondary.location_of_record == "CPNRSJ"
    assert secondary.travel_agent_city_code is None

    assert body[0] == "1AAAAA/RMR 1BBBBB/KMR 1FFFFF/LMR"


def test_record_locator_parse_directly():
    # RecordLocator.parse() exercised directly, independent of the
    # envelope parser, against the REQ03 p.49 example.
    rl = RecordLocator.parse("NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU")
    assert rl.booking_office == "NYC1G"
    assert rl.location_of_record == "CPNR1G"
    assert rl.iso_currency_code == "SU"  # 7th POS value, strictly positional


def test_record_locator_parse_missing_separator_raises():
    with pytest.raises(ValueError, match="missing booking office"):
        RecordLocator.parse("NOSPACEHERE")


def test_record_locator_parse_missing_location_of_record_raises():
    # Booking office + separator present, but the token after it is
    # entirely slashes (no location-of-record value at all).
    with pytest.raises(ValueError, match="missing location of record"):
        RecordLocator.parse("NYC1G //AAA")


def test_unverified_identifier_refuses_to_guess():
    # "MED" is in the identifier table (so it's *recognized*) but has no
    # verified has_record_locator entry -- the parser must refuse rather
    # than assume either True or False.
    raw = """\
QU HDQRMAA
.HDQRMBB 101234
MED
SOME BODY LINE HERE"""
    with pytest.raises(EnvelopeParseError, match="no verified record-locator behavior"):
        parse_envelope(raw)


def test_unknown_address_line_raises_clear_error():
    raw = "QU\n.HDQRMBB 101234"
    with pytest.raises(EnvelopeParseError, match="Address line malformed"):
        parse_envelope(raw)


def test_missing_comm_reference_raises_clear_error():
    raw = "QU HDQRMAA\nNOT A COMM REF LINE"
    with pytest.raises(EnvelopeParseError, match="communication reference"):
        parse_envelope(raw)


def test_too_short_message_raises_clear_error():
    with pytest.raises(EnvelopeParseError, match="too short"):
        parse_envelope("QU HDQRMAA")