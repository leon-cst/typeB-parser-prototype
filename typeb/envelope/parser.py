"""
Envelope parser: address block, communication reference, optional message
identifier, optional record locator.

"""
from __future__ import annotations

import re

from typeb.envelope.normalize import normalize_message
from typeb.model.envelope import Address, CommReference, Envelope, RecordLocator
from typeb.tables import loader

# name element = 1-3 digit "number in party" glued directly
# to the name/group text, no space (e.g. "1JOHN", "2SMITH", "25BALI/TOUR").
_NAME_LINE_RE = re.compile(r"^\d{1,3}\S")

_TERMINATORS = {"NNNN", "//"}


_DEFAULT_MAX_LINE_LENGTH = 69


class EnvelopeParseError(Exception):
    """Raised when the envelope structure can't be confidently parsed."""


def _looks_like_name_line(line: str) -> bool:
    return bool(_NAME_LINE_RE.match(line.strip()))


def _looks_like_terminator(line: str) -> bool:
    return line.strip() in _TERMINATORS


def parse_envelope(raw_message: str) -> tuple[Envelope, list[str]]:

    lines = normalize_message(raw_message).lines
    if len(lines) < 2:
        raise EnvelopeParseError(
            "Message too short to contain an envelope "
            "(need at least an address line and a communication "
            "reference line)"
        )

    idx = 0

    # Address block: priority code + one or more addresses
    address_tokens = lines[idx].strip().split()
    if len(address_tokens) < 2:
        raise EnvelopeParseError(
            f"Address line malformed, expected "
            f"'PRIORITY ADDR [ADDR ...]': {lines[idx]!r}"
        )
    priority_code, *address_strs = address_tokens
    try:
        addresses = [Address.parse(tok) for tok in address_strs]
    except ValueError as e:
        raise EnvelopeParseError(f"Address line malformed: {e}") from e
    idx += 1

    # Communication reference: ".<origin> <ddhhmm>" 
    if idx >= len(lines) or not lines[idx].strip().startswith("."):
        got = lines[idx] if idx < len(lines) else "<end of message>"
        raise EnvelopeParseError(
            f"Expected communication reference line starting with '.', "
            f"got: {got!r}"
        )
    comm_line = lines[idx].strip()[1:].strip()
    comm_tokens = comm_line.split()
    if not comm_tokens:
        raise EnvelopeParseError(
            f"Communication reference line has no origin address: "
            f"{lines[idx]!r}"
        )
    try:
        origin = Address.parse(comm_tokens[0])
    except ValueError as e:
        raise EnvelopeParseError(
            f"Communication reference origin address malformed: {e}"
        ) from e
    date_time_raw = " ".join(comm_tokens[1:])
    comm_reference = CommReference(origin=origin, date_time_raw=date_time_raw)
    idx += 1

    # Optional message identifier 
    message_identifier: str | None = None
    if idx < len(lines) and loader.is_known_message_identifier(lines[idx].strip()):
        message_identifier = lines[idx].strip()
        idx += 1

    # Optional record locator (0, 1, or 2 lines)
    has_record_locator = loader.identifier_has_record_locator(
        message_identifier or "BOOKING"
    )
    if has_record_locator is None:
        raise EnvelopeParseError(
            f"Message identifier "
            f"{message_identifier or '<implicit BOOKING>'!r} has no "
            f"verified record-locator behavior in the reference table "
            f"yet -- add meta.has_record_locator to "
            f"message_identifiers.yaml (with a spec citation) before "
            f"parsing this type. Refusing to guess."
        )

    record_locator_raw_lines: list[str] = []
    if has_record_locator:
        max_lines = 2  # primary + optional secondary, REQ03 p.9
        while (
            len(record_locator_raw_lines) < max_lines
            and idx < len(lines)
            and not _looks_like_name_line(lines[idx])
            and not _looks_like_terminator(lines[idx])
        ):
            record_locator_raw_lines.append(lines[idx].strip())
            idx += 1
        if not record_locator_raw_lines:
            got = lines[idx] if idx < len(lines) else "<end of message>"
            after = (
                f"identifier {message_identifier!r}"
                if message_identifier
                else "the communication reference"
            )
            raise EnvelopeParseError(
                f"Expected a record locator line after {after}, "
                f"got: {got!r}"
            )

    try:
        record_locators = [
            RecordLocator.parse(line) for line in record_locator_raw_lines
        ]
    except ValueError as e:
        raise EnvelopeParseError(f"Record locator line malformed: {e}") from e

    envelope = Envelope(
        priority_code=priority_code,
        addresses=addresses,
        comm_reference=comm_reference,
        message_identifier=message_identifier,
        record_locators=record_locators,
    )
    return envelope, lines[idx:]