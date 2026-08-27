"""
69-character line limit (REQ03 section 3). Previously fail-loud
(LineTooLongError); now advisory per coworker request:
  - Envelope lines (address, comm reference, identifier, record
    locator) are still parsed as best-effort, with a warning appended.
    There's no sensible way to "drop" a line the envelope structurally
    requires.
  - Body lines (NAME, SEGMENT, SSR, OSI, etc.) over the limit are
    excluded from parsing and land in unrecognized_lines, with a
    matching warning -- see typeb.messages.booking.

Note: excluding a NAME line can itself trigger a hard party-size
mismatch failure downstream (see typeb.elements.cross_reference,
validate_party_size fails loud on any mismatch by design) -- accepted,
since messages are machine-generated, not hand-typed, so a mismatch is
more likely a real upstream fault than a benign transcription quirk.
"""
import pytest

from typeb.elements.errors import ElementParseError
from typeb.envelope.parser import parse_envelope
from typeb.messages.booking import parse_booking_message


def test_line_at_exactly_69_chars_produces_no_warning():
    padding = "A" * (69 - len("QU CGKRM8G"))
    raw = f"QU CGKRM8G{padding}\n.NYCRM1G 050110\nNYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"
    _, _, warnings = parse_envelope(raw)
    assert warnings == []


def test_envelope_line_over_69_chars_still_parses_with_warning():
    padding = "A" * (70 - len("QU CGKRM8G"))
    raw = f"QU CGKRM8G{padding}\n.NYCRM1G 050110\nNYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"
    envelope, _, warnings = parse_envelope(raw)

    assert envelope.priority_code == "QU"
    assert len(warnings) == 1
    assert "70 characters" in warnings[0]
    assert "Line 1" in warnings[0]


def test_error_names_exact_line_number_and_length():
    raw = (
        "QU CGKRM8G\n"
        + "." + "A" * 79 + "\n"
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"
    )
    _, _, warnings = parse_envelope(raw)
    assert len(warnings) == 1
    assert "Line 2 is 80 characters" in warnings[0]


def test_too_long_body_line_excluded_then_party_size_mismatch_raises():
    # Excluding the over-length NAME line drops the declared party size
    # to 0, which no longer matches the segment's NN1 -- validate_party_size
    # now fails loud on any mismatch (see typeb.elements.cross_reference),
    # so this raises rather than returning a message with an empty
    # passengers list. Accepted tradeoff: messages are machine-generated,
    # not hand-typed, so a mismatch here is more likely a real upstream
    # fault than an acceptable transcription quirk.
    raw = (
        "QU CGKRM8G\n"
        ".NYCRM1G 050110\n"
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\n"
        "1" + "A" * 70 + "/BAMBANGMR\n"
        "8G083F24SEP CGKDPS NN1 0910 1015"
    )
    with pytest.raises(ElementParseError, match="total party size of 0"):
        parse_booking_message(raw)


def test_too_long_body_line_excluded_when_party_size_still_matches():
    # Same exclusion, but the segment requests 0 seats too (a passive
    # segment) -- confirms the exclusion itself doesn't block the rest
    # of the message from parsing when there's no resulting mismatch.
    raw = (
        "QU CGKRM8G\n"
        ".NYCRM1G 050110\n"
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\n"
        "1" + "A" * 70 + "/BAMBANGMR\n"
        "8G083F24SEP CGKDPS NN0 0910 1015"
    )
    msg = parse_booking_message(raw)

    assert msg.name_elements == []
    assert msg.passengers == []
    assert len(msg.unrecognized_lines) == 1
    assert len(msg.segments) == 1


def test_real_messages_from_project_history_produce_no_warnings():
    # REQ03 p.49 and the CONTOH-1..5 samples -- none should trip the
    # length check; a false positive here would mean the limit is
    # miscounted (e.g. off-by-one, or counting a trailing character
    # normalize_message should have already stripped).
    real_messages = [
        "QU CGKRM8G\n.NYCRM1G 050110\nNYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\n1RAHARJO/BAMBANGMR\n8G083F24SEP CGKDPS NN1 0910 1015",
        "QU TYORMNH\n.HDQRM1F 241310\nHDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY\n1AAAAA/TCCCMR\nMH123Y21DEC NRTLAX PK1/1705 0945\nSSR TKNE NH HK1 NRTLAX0123Y21DEC.2051234567890C1",
    ]
    for raw in real_messages:
        _, _, warnings = parse_envelope(raw)
        assert warnings == []