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
"""
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


def test_too_long_body_line_excluded_not_parsed():
    raw = (
        "QU CGKRM8G\n"
        ".NYCRM1G 050110\n"
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\n"
        "1" + "A" * 70 + "/BAMBANGMR\n"
        "8G083F24SEP CGKDPS NN1 0910 1015"
    )
    msg = parse_booking_message(raw)

    # excluded from real output, not force-parsed as a NAME element
    assert msg.name_elements == []
    assert msg.passengers == []

    assert len(msg.unrecognized_lines) == 1
    assert "exceeds" in msg.unrecognized_lines[0].reason

    assert any("exceeding the 69-character limit" in w for w in msg.warnings)


def test_too_long_body_line_does_not_block_other_lines_from_parsing():
    # The over-length NAME line is excluded, but the segment on the
    # next line still parses normally -- one bad line doesn't fail the
    # whole message.
    raw = (
        "QU CGKRM8G\n"
        ".NYCRM1G 050110\n"
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\n"
        "1" + "A" * 70 + "/BAMBANGMR\n"
        "8G083F24SEP CGKDPS NN1 0910 1015"
    )
    msg = parse_booking_message(raw)

    assert len(msg.segments) == 1
    assert msg.segments[0].airline_code == "8G"


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