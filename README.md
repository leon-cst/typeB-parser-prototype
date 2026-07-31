# Type B Parser -- Variant B

A from-scratch rebuild of the Type B parser/generator, built alongside the
original single-file `app.py` (see `typeb_parser_handoff.md` in the main
project) for direct comparison. Scope: **AVN, RVR, and booking-hold
messages** end-to-end -- raw Type B text in, structured JSON out via a
live Flask API -- built so adding more of REQ03's ~60 message identifiers
later doesn't require a rewrite.

**117 tests passing.** The full pipeline works: envelope parsing,
element parsing (NAME/SEGMENT/SSR/OSI/AVAILABILITY_LINE/RECAP_LINE),
passenger cross-referencing, and all three message-type orchestrators
are built and wired to `POST /parse`.

## Why a separate layout

The original parser has one function per message type
(`parse_availability`, `parse_rvr`, `parse_booking`, ...). Every new
message type meant a new parser written from scratch. But re-reading
REQ03 sections 3 and 7-13, every reservation message shares the same
envelope and the same handful of element types (NAME, SEGMENT, SSR, OSI,
markers) -- what differs between message types is *which elements are
required or forbidden*, not the elements themselves.

So this variant separates:

- `typeb/tables/` -- reference data (message identifiers, status codes,
  titles, etc.) as YAML, not Python conditionals
- `typeb/envelope/` -- address/comm-ref/record-locator parsing, plus
  input normalization (shared by every message type)
- `typeb/elements/` -- one parser per element type, plus the tokenizer
  that classifies body lines and the cross-reference layer that merges
  scattered passenger data (shared by every message type)
- `typeb/model/` -- typed Pydantic domain models
- `typeb/messages/` -- one orchestrator per message type (`booking.py`,
  `avn.py`, `rvr.py`), each combining envelope + tokenizer + element
  parsers + cross-referencing into one `raw text -> JSON model` function
- `typeb/profiles/` -- per-partner bilateral-agreement config (not built
  yet)
- `typeb/reply/` -- request -> reply transform rules (not built yet)

Adding a new message type later should mostly mean: a new file in
`typeb/messages/`, a new output model in `typeb/model/`, and golden test
files -- reusing the existing tokenizer, element parsers, and
cross-reference layer as-is.

## What's built

**Tables** (`typeb/tables/`) -- 9 reference tables, 69 message
identifiers, loaded and validated at import time. Fails fast and loudly
on a malformed table rather than misbehaving on first request.

**Envelope** (`typeb/envelope/`) -- address block (multi-address
capable), communication reference, optional message identifier, optional
record locator (0, 1, or 2 lines, per identifier). Whether a given
identifier carries a record locator is a table flag set only where a
real worked example confirms it -- unverified identifiers raise rather
than guess. Input normalization runs first and fixes only what's
unambiguous (CRLF, whitespace, case, blank lines) -- see
`typeb/envelope/normalize.py`'s docstring for the line between "safe to
nudge" and "don't guess."

**Elements** (`typeb/elements/`):
- `name.py` -- the NAME element, in **two separate logics**: shared
  surname (`3FORD/E/B/C`) and distinct surnames (multiple different
  people chained on one line, each fully spelled out, boundaries found
  by scanning for titles). Also handles the FOID/EXST/CBBG seat-modifier
  case and the "no given name at all" case (`1DUVALIER/MISS`).
- `segment.py` -- booking-context flight segments (glued
  airline+flight+RBD+date).
- `availability.py` -- AVN body lines (spaced fields -- a genuinely
  different shape from SEGMENT, not a bug).
- `recap.py` -- RVR body lines, **two shapes**: date-range-with-frequency
  and single-date-with-optional-route (route omitted means "ALL", not an
  error).
- `ssr.py` / `osi.py` -- FOID, INFT/CHLD, and the shared email/DOB
  contact-info shape (which both SSR and OSI can carry, with or without
  a 4-letter code).
- `cross_reference.py` -- matches OSI/SSR name-references back to NAME
  elements by `(surname, given_name, title)`, derives passenger type
  (ADT/CHD/INF), merges email/DOB/FOID. Raises on any ambiguity
  (conflicting type signals, unmatched references, duplicate keys)
  rather than guessing. Generic, not booking-specific.
- `tokenizer.py` -- classifies body lines by shape before dispatch.

**Messages** (`typeb/messages/`) -- `booking.py`, `avn.py`, `rvr.py`,
each a full orchestrator. Policy: a genuinely malformed line fails the
whole message; a structurally-fine-but-unimplemented line (e.g. an SSR
code beyond FOID/INFT/CHLD) is collected into `unrecognized_lines`
instead of blocking the rest of the parse.

**API** (`app.py`) -- `GET /health` (table load confirmation) and
`POST /parse` (raw Type B text in, dispatches automatically by message
identifier to the right orchestrator, returns
`{"data": {...}, "detected_msg_id": "..."}` or `{"error": "..."}` with a
400 on any parse failure).

## What's explicitly NOT built yet (flagged, not silently skipped)

- A genuinely mixed NAME line (some people sharing a surname, some not,
  in the same line) still correctly raises rather than guessing --
  distinct from the (now-handled) all-shared or all-distinct cases.
- Continuation lines (NAME lines exceeding 69 chars)
- Double-letter/space/hyphen collapsing in names
- The automated SSR format (NSST, SMSW, BIKE, meal codes, etc.) and
  OSI TKNO
- ARRIVAL element, structured record-locator parsing (POS breakdown)
- Reply generation (`typeb/reply/`) and partner profiles
  (`typeb/profiles/`)
- Several genuine spec ambiguities are recorded as `meta.source_note`
  fields in the YAML tables and as docstring notes in the relevant
  parsers rather than silently resolved -- grep `source_note` across
  `typeb/tables/data/*.yaml`, and check `typeb/elements/recap.py` and
  `typeb/elements/name.py` for the ones found during parser development.

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

Should show **117 passed**.

## Run the app

```bash
python app.py
```

In Hoppscotch:
- `GET http://localhost:5000/health` -- confirms tables loaded
- `POST http://localhost:5000/parse` -- body as **Text/Plain**, raw Type
  B message. Dispatches automatically based on the message's identifier
  (or the implicit booking type when there's no identifier line).

## Try it in a Python shell

```python
from typeb.messages.booking import parse_booking_message

raw = """QU CGKRM8G
.NYCRM1G 050110
NYC1G CPNR1G/AAA/111122223333/NYC/1G/NL/CHF/SU
1RAHARJO/BAMBANGMR
8G083F24SEP CGKDPS NN1 0910 1015"""

msg = parse_booking_message(raw)
print(msg.model_dump())
```

## Next step

The cross-reference and orchestration layers are done; the natural next
piece is either (a) the SSR/OSI codes still out of scope (automated
format, TKNO), or (b) starting on reply generation now that request
parsing produces a solid structured model to transform.