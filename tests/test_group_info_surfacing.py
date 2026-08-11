from typeb.messages.booking import parse_booking_message


def test_group_fare_and_contact_address_surfaced():
    raw = """\
QU JFKRMTW
.PARRMPA 051355
PARPA 115Y10AUG
5ARDMORE 3BATES 5DRUMMOND 3ENGLER 4HAYRES
5ZIMMERMAN 5CLARK
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720
SSR GRPS TW TCP30 SITA/TOUR
SSR GRPF TW YNC
SSR GRPF TW YNC PARNYCSTL FRF 3590
OSI TW CTCA NYC HOLIDAY INN AGT ABC TRAVEL"""
    msg = parse_booking_message(raw)

    assert len(msg.group_fare_info) == 2
    assert msg.group_fare_info[0].status_code == "YNC"
    assert msg.group_fare_info[1].detail == "PARNYCSTL FRF 3590"

    assert len(msg.contact_addresses) == 1
    assert msg.contact_addresses[0].action_code == "CTCA"
    assert msg.contact_addresses[0].detail == "NYC HOLIDAY INN AGT ABC TRAVEL"


def test_group_seat_request_surfaced():
    raw = """\
QU JFKRMTW
.PARRMPA 201521
PARPA 115Y10AUG
30SITA/TOUR
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720
SSR GRPF TW YNO
SSR GPST TW NN30 JFKSTL0209Y11AUG"""
    msg = parse_booking_message(raw)

    assert len(msg.group_seat_requests) == 1
    assert msg.group_seat_requests[0].number_in_party == 30
    assert msg.group_seat_requests[0].segment_reference_raw == "JFKSTL0209Y11AUG"


def test_grps_confirmed_party_size_matches_group_placeholder():
    raw = """\
QU JFKRMTW
.PARRMPA 051355
PARPA 115Y10AUG
25SITA/TOUR 5ARDMORE/BOB/SUE/TIM/TOM/TONY
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720
SSR GRPS TW TCP30 SITA/TOUR
SSR GRPF TW YLE13/GV30"""
    msg = parse_booking_message(raw)

    sita = next(g for g in msg.group_placeholders if g.surname == "SITA")
    assert sita.number_in_party == 25
    assert sita.confirmed_party_size == 30


def test_grps_with_no_matching_group_placeholder_leaves_confirmed_size_none():
    raw = """\
QU JFKRMTW
.PARRMPA 051355
PARPA 115Y10AUG
5ARDMORE 3BATES 5DRUMMOND 3ENGLER 4HAYRES
5ZIMMERMAN 5CLARK
DL119Y10AUG ORYJFK HK30/1435 1700
TW209Y11AUG JFKSTL NN30/1550 1720
SSR GRPS TW TCP30 SITA/TOUR"""
    msg = parse_booking_message(raw)

    assert all(g.confirmed_party_size is None for g in msg.group_placeholders)