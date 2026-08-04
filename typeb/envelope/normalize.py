"""
Input normalization: handles safe, unambiguous formatting noise before
any structural parsing happens.

Every change is logged.

Types of safe ambiguity resolved by this module:
  - CRLF/CR line endings -> LF
  - Leading/trailing whitespace per line
  - Lowercase -> uppercase
  - Fully blank lines.

"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizationChange:
    line_number: int  # 1-indexed, in the ORIGINAL (pre-normalization) input
    kind: str  # "uppercased" | "trimmed_whitespace" | "dropped_blank_line"
    before: str
    after: str | None  # None if the line was dropped entirely


@dataclass(frozen=True)
class NormalizationResult:
    lines: list[str]
    changes: list[NormalizationChange]

    @property
    def was_modified(self) -> bool:
        return len(self.changes) > 0


def normalize_message(raw_message: str) -> NormalizationResult:
    """Apply only the safe, unambiguous corrections described above.
    Idempotent -- normalizing already-clean input produces the same
    lines with an empty change log."""
    original_lines = raw_message.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    changes: list[NormalizationChange] = []
    result_lines: list[str] = []

    for i, line in enumerate(original_lines, start=1):
        if line.strip() == "":
            changes.append(NormalizationChange(i, "dropped_blank_line", line, None))
            continue

        working = line
        stripped = working.strip()
        if stripped != working:
            changes.append(NormalizationChange(i, "trimmed_whitespace", working, stripped))
            working = stripped

        upper = working.upper()
        if upper != working:
            changes.append(NormalizationChange(i, "uppercased", working, upper))
            working = upper

        result_lines.append(working)

    return NormalizationResult(lines=result_lines, changes=changes)
