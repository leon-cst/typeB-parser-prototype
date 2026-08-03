from __future__ import annotations

from typeb.elements.name import render_name_element
from typeb.elements.segment import render_segment_element
from typeb.envelope.render import render_address, render_comm_reference, render_record_locator
from typeb.model.elements import NameElement, SegmentElement
from typeb.model.envelope import Envelope


def render_reply(
    envelope: Envelope,
    name_elements: list[NameElement],
    segments: list[SegmentElement],
    include_terminator: bool = True,
) -> str:
    lines = [envelope.priority_code + " " + " ".join(render_address(a) for a in envelope.addresses)]
    lines.append(render_comm_reference(envelope.comm_reference))
    if envelope.message_identifier:
        lines.append(envelope.message_identifier)
    lines.extend(render_record_locator(rl) for rl in envelope.record_locators)
    lines.extend(render_name_element(n) for n in name_elements)
    lines.extend(render_segment_element(s) for s in segments)
    if include_terminator:
        lines.append("NNNN")
    return "\n".join(lines)