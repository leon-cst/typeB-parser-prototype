from typeb.elements.name import parse_name_element
from typeb.elements.segment import parse_segment_element
from typeb.envelope.parser import parse_envelope
from typeb.model.booking import BookingMessage
from typeb.reply.cases.booking_confirm import generate_booking_confirm_reply
from typeb.reply.decision import ReplyDecision, SegmentDecision


def _build_booking_message(raw: str) -> BookingMessage:
    envelope, body_lines = parse_envelope(raw)
    name_elements = [parse_name_element(body_lines[0])]
    segments = [parse_segment_element(body_lines[1])]
    return BookingMessage(
        envelope=envelope,
        passengers=[],
        name_elements=name_elements,
        segments=segments,
        airline_record_locators=[],
        warnings=[],
        unrecognized_lines=[],
    )


def test_req03_p49_booking_confirm_reply_matches_spec_exactly():
    request_raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015"""

    expected_reply = """\
QU NYCRM1G
.CGKRM8G 050215
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS KK1
NNNN"""

    message = _build_booking_message(request_raw)
    decision = ReplyDecision(
        reply_date_time_raw="050215",
        segment_decisions=[SegmentDecision(action_code="KK", number_in_party=1)],
    )

    reply = generate_booking_confirm_reply(message, decision)
    assert reply == expected_reply


def test_confirm_all_helper_produces_same_result():
    request_raw = """\
QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015"""

    message = _build_booking_message(request_raw)
    decision = ReplyDecision.confirm_all(message.segments, "050215")
    reply = generate_booking_confirm_reply(message, decision)
    assert "8G083F24SEP CGKDPS KK1" in reply