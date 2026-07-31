# Type B Parser -- Variant B

A from-scratch rebuild of the Type B parser/generator, built alongside the
original single-file `app.py` (see `typeb_parser_handoff.md` in the main
project) for direct comparison. Same functional scope for now --
**AVN, RVR, and booking-hold messages** -- but structured so adding the
rest of REQ03's ~60 message identifiers later doesn't require a rewrite.

## Why a separate layout

The original parser has one function per message type
(`parse_availability`, `parse_rvr`, `parse_booking`, ...). Every new
message type meant a new parser written from scratch. But re-reading
REQ03 sections 3 and 7-13, every reservation message shares the same
envelope and the same ~8 element types (NAME, SEGMENT, ARRIVAL, SSR, OSI,
AUX, markers) -- what differs between message types is *which elements
are required or forbidden*, not the elements themselves.

So this variant separates:

- `typeb/tables/` -- reference data (message identifiers, status codes,
  etc.) as YAML, not Python conditionals
- `typeb/envelope/` -- address/comm-ref/record-locator parsing (shared by
  every message type)
- `typeb/elements/` -- one parser per element type (shared by every
  message type)
- `typeb/model/` -- typed domain model
- `typeb/profiles/` -- per-partner bilateral-agreement config
- `typeb/reply/` -- request -> reply transform rules

Adding a new message type later should mostly mean: a profile entry
(which elements it uses) + golden test files, not new parsing code.

## Status: Steps 1-2 complete

- **Step 1** -- `typeb/tables/` -- every reference table loads and
  validates at startup (8 tables, 69 message identifiers).
- **Step 2** -- `typeb/model/envelope.py` + `typeb/envelope/parser.py` --
  address block, communication reference, optional message identifier,
  optional record locator. Structural, not line-number based: it
  classifies each line by shape (via `typeb.tables.loader`) rather than
  assuming a fixed position, so it isn't broken by multi-address messages
  or by identifiers (DVD, BPR, ...) that insert extra record-locator
  lines the original line-3/line-4 heuristic didn't expect.

  Whether a given message identifier carries a record locator at all is
  a table flag (`meta.has_record_locator` in `message_identifiers.yaml`),
  not a hardcoded assumption -- set only where a real worked spec example
  confirms it. Unverified identifiers raise a clear error rather than
  guessing (see `test_unverified_identifier_refuses_to_guess`).

- **Step 2.5** -- `typeb/envelope/normalize.py` -- input normalization,
  applied automatically before structural parsing. Fixes only what's
  *unambiguous*: CRLF line endings, stray whitespace, lowercase input
  (Type B's allowed character set is uppercase-only per REQ03 section 3,
  so correcting case can't lose information), and blank lines. Every
  correction is logged (`NormalizationResult.changes`), nothing is
  silently altered. Deliberately does **not** try to resolve genuine
  structural ambiguity -- glued vs. spaced fields, missing digits -- since
  REQ02/REQ03 attribute that variation to bilateral agreement between
  specific senders, and guessing wrong there produces a *confidently
  wrong* parse rather than a clear failure. That's handled later by
  per-partner profiles once we know who's sending, not by blanket
  coercion applied to everyone. See `tests/test_normalize.py` for the
  line between what gets fixed and what still fails loudly.

  Pydantic models also carry `str_strip_whitespace=True,
  str_to_upper=True` as defense-in-depth, for anyone constructing them
  directly without going through `parse_envelope()`.

Nothing below the envelope (NAME/SEGMENT/SSR/OSI elements, the body
tokenizer) is implemented yet.

While transcribing the three source PDFs into these tables, several
real contradictions and ambiguities in the spec turned up (OCR damage,
codes reused with different meanings under different headings, AVS
meaning something different in REQ02 vs REQ03). These are recorded as
`meta.source_note` fields directly on the relevant table entries rather
than silently resolved -- see `typeb/tables/loader.py`'s docstring for
the policy, and grep `source_note` across `typeb/tables/data/*.yaml` for
the full list. Worth reviewing with whoever owns the spec (I Wayan Parka)
before they matter in practice.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the tests

```bash
pytest -v
```

All tests should pass -- this only proves the reference tables are well-formed, not that any parsing works yet (there isn't any yet).

## Run the app

```bash
python app.py
```

Then in Hoppscotch: `GET http://localhost:5000/health` should return
`{"status": "ok", "tables_loaded": {...counts per table...}}`. If any
table is malformed, the app will refuse to start at all -- check the
traceback, it will name the file and the problem.

## Try the envelope parser yourself

```python
from typeb.envelope.parser import parse_envelope

raw = """QU FTWRMAA
.HDQRI8G 201025
AVN
AA800 F 01JUN CGKDPS
NNNN"""

envelope, body_lines = parse_envelope(raw)
print(envelope.model_dump())
print(body_lines)
```

## Next step

Step 3: the element layer -- NAME, SEGMENT, ARRIVAL, SSR, OSI parsers,
plus the body tokenizer that groups raw body lines (the `body_lines`
returned by `parse_envelope`) into elements before dispatching each to
its parser. This is where `split_glued_title` and the passenger-matching
question from the original project's handoff come back into play, now
against a shared element model instead of being booking-specific.
