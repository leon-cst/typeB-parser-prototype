"""Shared exception types for the element layer, used by every parser in
typeb.elements.*."""


class ElementParseError(Exception):
    """Raised when a body line doesn't match its expected element shape."""


class UnrecognizedElementError(ElementParseError):
    """This is a more specific case: the line IS a structurally valid instance
    of a known element family (e.g. it starts with 'SSR' and has the
    right general shape) but no parser has been implemented yet for its
    specific code/shape"""