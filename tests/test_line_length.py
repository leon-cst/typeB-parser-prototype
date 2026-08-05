import pytest

from typeb.envelope.parser import LineTooLongError, parse_envelope


def test_line_at_exactly_69_chars_is_accepted():
    padding = "A" * (69 - len("QU CGKRM8G"))
    raw = f"QU CGKRM8G{padding}\n.NYCRM1G 050110"
    # Only asserting this doesn't raise LineTooLongError -- address
    # shape validity isn't this test's concern.
    try:
        parse_envelope(raw)
    except LineTooLongError:
        pytest.fail("69-character line should not raise LineTooLongError")
    except Exception:
        pass


def test_line_at_70_chars_raises():
    padding = "A" * (70 - len("QU CGKRM8G"))
    raw = f"QU CGKRM8G{padding}\n.NYCRM1G 050110"
    with pytest.raises(LineTooLongError, match="70 characters"):
        parse_envelope(raw)


def test_too_long_name_line_raises():
    raw = (
        "QU CGKRM8G\n"
        ".NYCRM1G 050110\n"
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\n"
        "1" + "A" * 70 + "/BAMBANGMR\n"
        "8G083F24SEP CGKDPS NN1 0910 1015"
    )
    with pytest.raises(LineTooLongError, match="Line 4"):
        parse_envelope(raw)


def test_error_names_exact_line_number_and_length():
    raw = "QU CGKRM8G\n" + "A" * 80
    with pytest.raises(LineTooLongError, match=r"Line 2 is 80 characters"):
        parse_envelope(raw)


def test_real_messages_from_project_history_all_pass():
    # REQ03 p.49 and the CONTOH-1..5 samples -- none should trip the
    # length check; a false positive here would mean the limit is
    # miscounted (e.g. off-by-one, or counting a trailing character
    # normalize_message should have already stripped).
    real_messages = [
        "QU CGKRM8G\n.NYCRM1G 050110\nNYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\n1RAHARJO/BAMBANGMR\n8G083F24SEP CGKDPS NN1 0910 1015",
        "QU TYORMNH\n.HDQRM1F 241310\nHDQ1F CPNR1F/8HH6/12345678/TYO/1F/T/JP/JPY\n1AAAAA/TCCCMR\nMH123Y21DEC NRTLAX PK1/1705 0945\nSSR TKNE NH HK1 NRTLAX0123Y21DEC.2051234567890C1",
    ]
    for raw in real_messages:
        parse_envelope(raw)  # should not raise