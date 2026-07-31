"""
Tokenizer tests. Includes a specific regression case for a real bug
found during development: a naive NAME-line regex (digit(s) followed by
any non-space char) also matches SEGMENT lines whose airline code starts
with a digit (8G, 5J, 3U, 9C, ...) -- see tokenizer.py's module docstring
for the fix and reasoning.
"""
from typeb.elements.tokenizer import ElementKind, classify_line, tokenize_body


def test_name_line_classified_correctly():
    assert classify_line("1RAHARJO/BAMBANGMR") == ElementKind.NAME
    assert classify_line("2BORGE/A/D") == ElementKind.NAME


def test_segment_line_classified_correctly():
    assert classify_line("8G083F24SEP CGKDPS NN1 0910 1015") == ElementKind.SEGMENT
    assert classify_line("SJ920Y15FEB SINAMS XX1") == ElementKind.SEGMENT


def test_digit_led_airline_segment_not_misclassified_as_name():
    # Regression case: "8G083F24SEP..." starts with "8" then "G" -- a
    # digit followed by a non-space character, which a naive NAME regex
    # would match. Must classify as SEGMENT, not NAME.
    assert classify_line("8G083F24SEP CGKDPS NN1 0910 1015") != ElementKind.NAME
    assert classify_line("8G083F24SEP CGKDPS NN1 0910 1015") == ElementKind.SEGMENT

    # Same check for other real digit-led IATA airline codes.
    assert classify_line("5J123Y01JUN MNLCEB HK1 0800 0930") == ElementKind.SEGMENT
    assert classify_line("3U809Y15FEB PEKCTU HK1 1000 1300") == ElementKind.SEGMENT


def test_availability_line_classified_correctly():
    assert classify_line("AA800 F 01JUN CGKDPS") == ElementKind.AVAILABILITY_LINE
    # Digit-led airline code, spaced format
    assert classify_line("8G800 Y 01JUN CGKDPS") == ElementKind.AVAILABILITY_LINE


def test_recap_line_classified_correctly():
    assert classify_line("8G407/16JUN26-30DEC26/1234567") == ElementKind.RECAP_LINE
    # Single-date shape (REQ02 p.14) -- this is the case that was
    # originally misclassified as UNKNOWN before this rule was fixed to
    # recognize both documented shapes, not just the date-range one.
    assert classify_line("8G123/16JUN26 CGKSIN") == ElementKind.RECAP_LINE
    assert classify_line("8G123/16JUN26") == ElementKind.RECAP_LINE  # route omitted


def test_ssr_line_classified_correctly():
    assert classify_line("SSR FOID 8G HK1/8472910483756291-2KUSUMA/BUDISANTOSO/MR") == ElementKind.SSR
    assert classify_line("SSR INFT 8G 1ANGGARA/BAYIBUDI/MR") == ElementKind.SSR


def test_osi_line_classified_correctly():
    assert classify_line("OSI 8G 1 CHD 1PRATAMA/ARIELUCY/MSTR") == ElementKind.OSI
    assert classify_line("OSI GA 1BAMBANG/MR E/BABANG@GMAIL.COM") == ElementKind.OSI


def test_marker_lines_classified_correctly():
    assert classify_line("NNNN") == ElementKind.MARKER
    assert classify_line("ARNK") == ElementKind.MARKER
    assert classify_line("//") == ElementKind.MARKER


def test_unrecognized_line_classified_as_unknown():
    assert classify_line("THIS IS NOT A KNOWN SHAPE AT ALL") == ElementKind.UNKNOWN


def test_tokenize_body_preserves_order_and_raw_text():
    body = [
        "1RAHARJO/BAMBANGMR",
        "8G083F24SEP CGKDPS NN1 0910 1015",
        "NNNN",
    ]
    result = tokenize_body(body)
    assert result == [
        (ElementKind.NAME, "1RAHARJO/BAMBANGMR"),
        (ElementKind.SEGMENT, "8G083F24SEP CGKDPS NN1 0910 1015"),
        (ElementKind.MARKER, "NNNN"),
    ]