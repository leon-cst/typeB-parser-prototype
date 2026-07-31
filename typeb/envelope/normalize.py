"""
Input normalization -- handles safe, unambiguous formatting noise before
any structural parsing happens.

Deliberately does NOT attempt to resolve genuine structural ambiguity
(glued vs. spaced fields, missing digits, OCR-style corruption). See the
module-level docstring on parse_envelope() for why -- in short, REQ02/
REQ03 attribute that kind of variation to bilateral agreement between
specific senders, so guessing at it here would mean silently producing a
plausible-looking but potentially wrong parse. That's handled later by
per-partner profiles, once we actually know who's sending, not by
blanket coercion applied to everyone.

What this module DOES fix is safe because it's unambiguous:

  - CRLF/CR line endings -> LF: a transmission/copy-paste artifact,
    never semantically meaningful.
  - Leading/trailing whitespace per line: Type B has no semantic use for
    padding; REQ03's line-length limit counts content, not padding.
  - Lowercase -> uppercase: REQ03 section 3 states the allowed character
    set is A-Z, 0-9, '/', '-', '.' only. Lowercase is never valid Type B,
    so correcting it can't lose information the way, say, guessing a
    glued field boundary could.
  - Fully blank lines: never carry meaning; typically copy-paste padding.

Every change is logged, not applied silently -- nothing here should be
invisible if someone later needs to know a message needed correcting
(e.g. to notice a partner integration is consistently sending lowercase
and should be fixed at the source, even though we recovered from it).
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
