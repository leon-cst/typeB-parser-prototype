"""
Type B message parser/generator -- Variant B (foundation-first rebuild).

Layout (each layer is independently testable):
    tables/     reference data -- message identifiers, status codes, etc.

    envelope/   address block, comm reference, record locator parsing

    elements/   NAME / SEGMENT / ARRIVAL / SSR / OSI / marker parsers

    model/      typed domain model tying envelope + elements together

    profiles/   per-partner bilateral-agreement config (glued vs spaced
                fields, line length, terminator, etc.)
                
    reply/      request -> reply transform rules
"""
