"""Shared exception types for the element layer, used by every parser in
typeb.elements.*."""


class ElementParseError(Exception):
    """Raised when a body line doesn't match its expected element shape.
    Genuine malformation -- the line claims to be a specific,
    implemented shape but doesn't match it."""


class UnrecognizedElementError(ElementParseError):
    """A more specific case: the line IS a structurally valid instance
    of a known element family (e.g. it starts with 'SSR' and has the
    right general shape) but no parser has been implemented yet for its
    specific code/shape -- as opposed to a plain ElementParseError,
    which means the line doesn't match its expected format at all.

    Subclasses ElementParseError so existing code catching that broadly
    still catches this. Orchestration code (typeb.messages.booking)
    treats this specifically as "unrecognized, collect and continue"
    rather than failing the whole message -- a real message containing
    one out-of-scope SSR code shouldn't block parsing everything else."""