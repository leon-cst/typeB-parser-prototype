"""
Element parsers -- NAME, SEGMENT, ARRIVAL, SSR, OSI, AUX, and markers
(ARNK, CHNT, NNNN).

Not built yet (Step 3). Each parser will be a pure function
str -> ElementModel, with a matching render() so reply generation is a
model transform, not string concatenation from scratch.
"""
