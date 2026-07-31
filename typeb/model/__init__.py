"""
Domain model tying envelope + elements into one TypeBMessage.

Built with Pydantic v2 (frozen/immutable models). envelope.py has
Address / CommReference / Envelope. The element-bearing models (NAME,
SEGMENT, SSR, OSI, etc.) and the top-level TypeBMessage that ties
envelope + elements together come in Step 3.
"""
