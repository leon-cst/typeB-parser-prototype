from typeb.elements.name import render_name_element
from typeb.elements.segment import parse_segment_element, render_segment_element
from typeb.envelope.render import (
    render_address,
    render_comm_reference,
    render_record_locator,
)
from typeb.model.elements import NameElement, Person
from typeb.model.envelope import Address, CommReference, RecordLocator


def test_render_address():
    a = Address.parse("CGKRM8G")
    assert render_address(a) == "CGKRM8G"


def test_render_comm_reference():
    c = CommReference(origin=Address.parse("NYCRM1G"), date_time_raw="050110")
    assert render_comm_reference(c) == ".NYCRM1G 050110"


def test_render_record_locator_with_pos_fields():
    rl = RecordLocator.parse("NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU")
    assert render_record_locator(rl) == "NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU"


def test_render_record_locator_no_pos_fields():
    rl = RecordLocator.parse("CGK8G CPNR8G")
    assert render_record_locator(rl) == "CGK8G CPNR8G"


def test_render_segment_with_times():
    s = parse_segment_element("8G083F24SEP CGKDPS NN1 0910 1015")
    assert render_segment_element(s) == "8G083F24SEP CGKDPS NN1 0910 1015"


def test_render_segment_no_times():
    s = parse_segment_element("SJ920Y15FEB SINAMS XX1")
    assert render_segment_element(s) == "SJ920Y15FEB SINAMS XX1"


def test_render_name_shared_surname_single_person():
    n = NameElement(
        raw="1RAHARJO/BAMBANGMR",
        number_in_party=1,
        surname="RAHARJO",
        people=[Person(given_name="BAMBANG", title="MR")],
        is_group_placeholder=False,
        seat_modifiers=[],
        uses_distinct_surnames=False,
    )
    assert render_name_element(n) == "1RAHARJO/BAMBANGMR"


def test_render_name_shared_surname_multi_person():
    n = NameElement(
        raw="3FORD/E/B/C",
        number_in_party=3,
        surname="FORD",
        people=[
            Person(given_name="E", title=None),
            Person(given_name="B", title=None),
            Person(given_name="C", title=None),
        ],
        is_group_placeholder=False,
        seat_modifiers=[],
        uses_distinct_surnames=False,
    )
    assert render_name_element(n) == "3FORD/E/B/C"


def test_render_name_seat_modifier():
    n = NameElement(
        raw="2DOOLEY/ALBERTMR/EXST",
        number_in_party=2,
        surname="DOOLEY",
        people=[Person(given_name="ALBERT", title="MR")],
        is_group_placeholder=False,
        seat_modifiers=["EXST"],
        uses_distinct_surnames=False,
    )
    assert render_name_element(n) == "2DOOLEY/ALBERTMR/EXST"


def test_render_name_distinct_surnames():
    n = NameElement(
        raw="2WIJAYA/RINAMAHARANI/MRS/SIREGAR/BAYIRINA/MSTR",
        number_in_party=2,
        surname="WIJAYA",
        people=[
            Person(surname="WIJAYA", given_name="RINAMAHARANI", title="MRS"),
            Person(surname="SIREGAR", given_name="BAYIRINA", title="MSTR"),
        ],
        is_group_placeholder=False,
        seat_modifiers=[],
        uses_distinct_surnames=True,
    )
    assert render_name_element(n) == "2WIJAYA/RINAMAHARANI/MRS/SIREGAR/BAYIRINA/MSTR"


def test_render_name_group_placeholder():
    n = NameElement(
        raw="6SEAMEN",
        number_in_party=6,
        surname="SEAMEN",
        people=[],
        is_group_placeholder=True,
        seat_modifiers=[],
        uses_distinct_surnames=False,
    )
    assert render_name_element(n) == "6SEAMEN"