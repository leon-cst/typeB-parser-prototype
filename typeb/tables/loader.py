"""
Reference table loader for the Type B parser.

Design rule (REQ03 section 5 says this explicitly about the message
identifier table: "agar dibuat dalam File Table tersendiri" -- "should be
made into its own file table"): anything the spec presents as a bulleted
list of codes belongs here as data, not as Python if/elif chains. Adding a
new code the spec supports should mean editing a YAML file, not touching
parser logic.

Every table is loaded once and validated eagerly. A malformed table raises
TableLoadError immediately -- we want the app to refuse to start rather
than fail confusingly on whichever request happens to touch the bad table
first. app.py loads every table at import time for exactly this reason.

Duplicate-code policy: a code must be unique *within one table file*.
Several codes in the source spec are genuinely reused across different
category headings with different (or subtly different) meanings -- e.g.
PN = "Pending need" under one heading and "Passive request" under another.
Rather than silently pick a winner, ambiguous entries carry a
meta.source_note flagging the alternate meaning, so a human resolves it
instead of the loader guessing. See segment_status_codes.yaml for examples.
"""
from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).parent / "data"

_NUMERIC_AVAILABILITY_RE = re.compile(r"^([AL])([0-9])$")


class TableLoadError(Exception):
    """Raised when a reference table is malformed. Meant to fail at startup."""


@dataclass(frozen=True)
class CodeEntry:
    code: str
    description: str
    category: str | None = None
    meta: dict[str, Any] | None = None


def _load_yaml(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        raise TableLoadError(f"Missing reference table: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "entries" not in data:
        raise TableLoadError(f"{filename}: expected a top-level 'entries' list")
    return data


def _build_registry(filename: str) -> dict[str, CodeEntry]:
    data = _load_yaml(filename)
    entries = data["entries"]
    if not isinstance(entries, list):
        raise TableLoadError(f"{filename}: 'entries' must be a list")

    registry: dict[str, CodeEntry] = {}
    for i, raw in enumerate(entries):
        for field in ("code", "description"):
            if field not in raw:
                raise TableLoadError(
                    f"{filename}: entry #{i} missing required field "
                    f"'{field}': {raw}"
                )
        code = raw["code"]
        if code in registry:
            raise TableLoadError(
                f"{filename}: duplicate code '{code}' -- if this is a "
                f"genuinely reused code with a different meaning, keep one "
                f"entry and record the alternate meaning in meta.source_note "
                f"instead of adding a second row."
            )
        registry[code] = CodeEntry(
            code=code,
            description=raw["description"],
            category=raw.get("category"),
            meta=raw.get("meta"),
        )
    return registry


@functools.lru_cache(maxsize=None)
def _registry(filename: str) -> dict[str, CodeEntry]:
    return _build_registry(filename)


# --------------------------------------------------------------------------
# Public tables
# --------------------------------------------------------------------------

def message_identifiers() -> dict[str, CodeEntry]:
    return _registry("message_identifiers.yaml")


def segment_status_codes() -> dict[str, CodeEntry]:
    return _registry("segment_status_codes.yaml")


def avn_status_codes() -> dict[str, CodeEntry]:
    return _registry("avn_status_codes.yaml")


def error_codes() -> dict[str, CodeEntry]:
    return _registry("error_codes.yaml")


def aux_service_codes() -> dict[str, CodeEntry]:
    return _registry("aux_service_codes.yaml")


def osi_contact_codes() -> dict[str, CodeEntry]:
    return _registry("osi_contact_codes.yaml")


def payment_type_codes() -> dict[str, CodeEntry]:
    return _registry("payment_type_codes.yaml")


def office_function_codes() -> dict[str, CodeEntry]:
    return _registry("office_function_codes.yaml")

def name_title_codes() -> dict[str, CodeEntry]:
    return _registry("name_title_codes.yaml")


# --------------------------------------------------------------------------
# Convenience lookups
# --------------------------------------------------------------------------

def is_known_message_identifier(code: str) -> bool:
    return code in message_identifiers()


def get_message_identifier(code: str) -> CodeEntry | None:
    return message_identifiers().get(code)


def is_supported_message_identifier(code: str) -> bool:
    """True only for identifiers this parser currently implements
    (AVN, RVR, and the synthetic BOOKING pseudo-identifier). Everything
    else in the table is recognized/documented but not yet parsed --
    that's the whole point of loading the full table now."""
    entry = get_message_identifier(code)
    return bool(entry and entry.meta and entry.meta.get("supported"))


def identifier_has_record_locator(code: str) -> bool | None:
    """Whether messages of this identifier carry a record locator line
    (or two -- see BPR) immediately following the identifier. Returns
    None if we don't have a verified worked example for this identifier
    yet -- callers should treat None as "unknown, don't guess", not as
    False. See message_identifiers.yaml for the evidence behind each
    True/False value."""
    entry = get_message_identifier(code)
    if entry is None or entry.meta is None:
        return None
    return entry.meta.get("has_record_locator")


def match_numeric_availability_code(code: str) -> dict[str, Any] | None:
    """A0-A9 / L0-L9 (REQ02 p.6): the digit is the seat count currently
    available and replaces whatever status applied before. This is
    parametric, not enumerable, so it isn't a table row -- it's a pattern
    match. 'L' prefix carries request-only semantics; 'A' does not."""
    m = _NUMERIC_AVAILABILITY_RE.match(code)
    if not m:
        return None
    prefix, digit = m.groups()
    return {
        "prefix": prefix,
        "seats_available": int(digit),
        "category": (
            "numeric_availability" if prefix == "A"
            else "numeric_availability_request_only"
        ),
    }


def load_all() -> dict[str, dict[str, CodeEntry]]:
    """Load + validate every table. Call this once at app startup so a
    malformed table fails the app immediately instead of on first request."""
    return {
        "message_identifiers": message_identifiers(),
        "segment_status_codes": segment_status_codes(),
        "avn_status_codes": avn_status_codes(),
        "error_codes": error_codes(),
        "aux_service_codes": aux_service_codes(),
        "osi_contact_codes": osi_contact_codes(),
        "payment_type_codes": payment_type_codes(),
        "office_function_codes": office_function_codes(),
        "name_title_codes": name_title_codes(),
    }
