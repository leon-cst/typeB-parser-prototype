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
    assert envelope.record_locator_lines == []  # availability family: none

    assert body[0] == "AA800 F 01JUN CGKDPS"
    assert body[-1] == "NNNN"


def test_rvr_envelope_has_no_record_locator():
    # REQ03 p.13 -- real request example (trailing Indonesian commentary
    # on the source page, "berlaku untuk all route flight", is the
    # document's own explanatory annotation and is dropped here, not
    # part of the wire message)
    raw = """\
QU HDQRI8G
.JKTRM1G 161102
RVR
8G407/16JUN26-30DEC26/1234567
NNNN"""
    envelope, body = parse_envelope(raw)

    assert envelope.message_identifier == "RVR"
    assert envelope.record_locator_lines == []
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
    assert envelope.record_locator_lines == [
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"
    ]
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
    assert envelope.record_locator_lines == ["CPHSK 1713"]
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
    assert envelope.record_locator_lines == ["HDQ8G CPNRSJ/ABC/12345678/LON/1G/T/GB"]
    assert body[0] == "1AAAAA/MR"
    assert body[1] == "SJ920Y15FEB SINAMS XX1"


def test_bpr_double_record_locator():
    # REQ03 p.62 -- real BPR example with a primary AND secondary record
    # locator line (REQ03 p.9's "bilateral agreement" primary/secondary
    # rule in practice) before the name element
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
    assert envelope.record_locator_lines == [
        "HDR1B CPNR1B/MADIB0500/1234567/////",
        "HDQSJ CPNRSJ",
    ]
    assert body[0] == "1AAAAA/RMR 1BBBBB/KMR 1FFFFF/LMR"


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
