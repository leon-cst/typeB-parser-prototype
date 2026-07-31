"""
Type B message parser/generator -- Variant B (foundation-first rebuild).

Layout (each layer is independently testable):
    tables/     reference data -- message identifiers, status codes, etc.
                (Step 1 -- built now)
    envelope/   address block, comm reference, record locator parsing
                (Step 2)
    elements/   NAME / SEGMENT / ARRIVAL / SSR / OSI / marker parsers
                (Step 3)
    model/      typed domain model tying envelope + elements together
                (Step 3-4)
    profiles/   per-partner bilateral-agreement config (glued vs spaced
                fields, line length, terminator, etc.)
                (Step 5+)
    reply/      request -> reply transform rules
                (Step 5+)
"""
