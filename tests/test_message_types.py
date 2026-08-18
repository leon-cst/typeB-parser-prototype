"""
Cross-type smoke tests: one real message per currently-supported
message type (AVN, RVR, BOOKING, DVD), run end-to-end through the same
_ORCHESTRATORS dispatch app.py uses. Narrow per-feature tests for each
type live in their own test_*.py files; this file is a single place to
confirm every supported type still parses cleanly after any change.
"""
from typeb.envelope.parser import parse_envelope
from typeb.messages.avn import parse_availability_message
from typeb.messages.booking import parse_booking_message
from typeb.messages.dvd import parse_dvd_message
from typeb.messages.rvr import parse_recap_message

_ORCHESTRATORS = {
    "AVN": parse_availability_message,
    "RVR": parse_recap_message,
    "BOOKING": parse_booking_message,
    "DVD": parse_dvd_message,
}

_MESSAGES = {
    "AVN": """\
QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
AA800 J 01JUN CGKDPS
AA800 Y 01JUN CGKDPS
AA800 B 01JUN CGKDPS
NNNN""",
    "RVR": """\
QU HDQRI8G
.JKTRM1G 161102
RVR
8G407/16JUN26-30DEC26/1234567
NNNN""",
    "BOOKING": """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015""",
    "DVD": """\
QU CGKRMSJ
.HDQRM8G 101234
DVD
HDQ8G CPNRSJ/ABC/12345678/LON/1G/T/GB
1AAAAA/MR
SJ920Y15FEB SINAMS XX1
8G320Y15FEB CGKSIN HK1/1030 1210
SJ890Y15FEB SINLON SS1/1350 1610
OSI YY RLOC HDQ8GCPNRSJ""",
}


def test_every_supported_type_dispatches_and_parses_cleanly():
    for expected_type, raw in _MESSAGES.items():
        envelope, _, _ = parse_envelope(raw)
        assert envelope.effective_identifier == expected_type, (
            f"{expected_type} fixture dispatched as "
            f"{envelope.effective_identifier!r} instead"
        )

        msg = _ORCHESTRATORS[expected_type](raw)
        # AVN/RVR don't have a warnings field (see typeb.messages.avn/rvr)
        if hasattr(msg, "warnings"):
            assert msg.warnings == [], f"{expected_type}: unexpected warnings {msg.warnings}"
        assert msg.unrecognized_lines == [], (
            f"{expected_type}: unexpected unrecognized_lines {msg.unrecognized_lines}"
        )


def test_avn_fixture_content():
    msg = parse_availability_message(_MESSAGES["AVN"])
    assert len(msg.availability_lines) == 4
    assert msg.availability_lines[0].airline_code == "AA"


def test_rvr_fixture_content():
    msg = parse_recap_message(_MESSAGES["RVR"])
    assert len(msg.recap_lines) == 1
    assert msg.recap_lines[0].date_range_raw == "16JUN26-30DEC26"


def test_booking_fixture_content():
    msg = parse_booking_message(_MESSAGES["BOOKING"])
    assert len(msg.passengers) == 1
    assert msg.passengers[0].surname == "RAHARJO"
    assert len(msg.segments) == 1


def test_dvd_fixture_content():
    msg = parse_dvd_message(_MESSAGES["DVD"])
    assert len(msg.passengers) == 1
    assert len(msg.segments) == 3
    assert len(msg.original_locators) == 1


def test_each_orchestrator_rejects_every_other_types_fixture():
    # Cross-check: an AVN orchestrator must refuse a BOOKING message,
    # a DVD orchestrator must refuse an AVN message, etc. -- confirms
    # the identifier guard in each orchestrator is doing its job for
    # every pairing, not just the one pairing each type's own test file
    # happens to check.
    for orchestrator_type, orchestrator in _ORCHESTRATORS.items():
        for fixture_type, raw in _MESSAGES.items():
            if fixture_type == orchestrator_type:
                continue
            try:
                orchestrator(raw)
            except Exception as e:
                assert "non-" in str(e) or "Unexpected" in str(e), (
                    f"{orchestrator_type} orchestrator given a "
                    f"{fixture_type} fixture raised an unexpected "
                    f"error shape: {e}"
                )
            else:
                raise AssertionError(
                    f"{orchestrator_type} orchestrator accepted a "
                    f"{fixture_type} fixture without complaint"
                )