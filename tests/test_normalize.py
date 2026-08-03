"""
Tests for normalize.py -- the "safe nudging" layer.
Split into two groups: normalize_message() tested directly,
and full parse_envelope() tests proving that deliberately messy
input parses identically to clean input for the safe categories,
while genuinely ambiguous/malformed input still fails clearly.
"""
import pytest

from typeb.envelope.normalize import normalize_message
from typeb.envelope.parser import EnvelopeParseError, parse_envelope


def test_crlf_line_endings_normalized():
    result = normalize_message("QU HDQRMAA\r\n.HDQRMBB 101234\r\n")
    assert result.lines == ["QU HDQRMAA", ".HDQRMBB 101234"]
    kinds = {c.kind for c in result.changes}
    assert "trimmed_whitespace" not in kinds  # CRLF isn't logged as whitespace-trim
    assert "dropped_blank_line" in kinds  # trailing \r\n leaves one blank line


def test_leading_trailing_whitespace_stripped_and_logged():
    result = normalize_message("  QU HDQRMAA  \n.HDQRMBB 101234")
    assert result.lines == ["QU HDQRMAA", ".HDQRMBB 101234"]
    assert result.was_modified
    change = next(c for c in result.changes if c.kind == "trimmed_whitespace")
    assert change.before == "  QU HDQRMAA  "
    assert change.after == "QU HDQRMAA"


def test_lowercase_uppercased_and_logged():
    result = normalize_message("qu hdqrmaa\n.hdqrmbb 101234")
    assert result.lines == ["QU HDQRMAA", ".HDQRMBB 101234"]
    change = next(c for c in result.changes if c.kind == "uppercased")
    assert change.before == "qu hdqrmaa"
    assert change.after == "QU HDQRMAA"


def test_blank_lines_dropped_and_logged():
    result = normalize_message("QU HDQRMAA\n\n\n.HDQRMBB 101234")
    assert result.lines == ["QU HDQRMAA", ".HDQRMBB 101234"]
    dropped = [c for c in result.changes if c.kind == "dropped_blank_line"]
    assert len(dropped) == 2


def test_clean_input_produces_no_changes():
    result = normalize_message("QU HDQRMAA\n.HDQRMBB 101234")
    assert result.was_modified is False
    assert result.changes == []


def test_normalization_is_idempotent():
    messy = "  qu hdqrmaa  \n\n.hdqrmbb 101234\r\n"
    once = normalize_message(messy)
    twice = normalize_message("\n".join(once.lines))
    assert once.lines == twice.lines
    assert twice.changes == []  # nothing left to fix the second time


# --------------------------------------------------------------------------
# Full parse_envelope() proof: messy input parses identically to clean
# --------------------------------------------------------------------------

_CLEAN_AVN = """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
NNNN"""


def test_messy_avn_parses_identically_to_clean():
    messy = """\
  qu ftwrmaa
.hdqri8g   201025
avn

aa800 f 01jun cgkdps
nnnn
"""
    clean_envelope, clean_body = parse_envelope(_CLEAN_AVN)
    messy_envelope, messy_body = parse_envelope(messy)

    assert messy_envelope == clean_envelope
    assert messy_body == clean_body


def test_crlf_and_extra_blank_lines_dont_break_booking_parse():
    # Same p.49 booking example as test_envelope.py, deliberately mangled
    # with CRLF endings and stray blank lines.
    messy = (
        "QU CGKRM8G\r\n"
        "\r\n"
        ".NYCRM1G 050110\r\n"
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU\r\n"
        "\r\n"
        "1RAHARJO/BAMBANGMR\r\n"
        "8G083F24SEP CGKDPS NN1 0910 1015\r\n"
    )
    envelope, body = parse_envelope(messy)
    assert envelope.message_identifier is None
    assert len(envelope.record_locators) == 1
    assert envelope.record_locators[0].raw == (
        "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"
    )
    assert envelope.record_locators[0].iso_currency_code == "SU"
    assert body[0] == "1RAHARJO/BAMBANGMR"


# --------------------------------------------------------------------------
# Check whether genuinely structural problems still fail clearly,
# Tests for overcorrection
# --------------------------------------------------------------------------

def test_genuinely_short_address_still_rejected_after_normalization():
    # Lowercase + whitespace noise gets fixed; the address itself being
    # too short to contain a valid city+office+designator does not.
    raw = "  qu ab  \n.hdqrmbb 101234"
    with pytest.raises(EnvelopeParseError, match="Address line malformed"):
        parse_envelope(raw)


def test_unverified_identifier_still_refuses_to_guess_after_normalization():
    raw = "qu hdqrmaa\n.hdqrmbb 101234\nmed\nsome body line"
    with pytest.raises(EnvelopeParseError, match="no verified record-locator behavior"):
        parse_envelope(raw)