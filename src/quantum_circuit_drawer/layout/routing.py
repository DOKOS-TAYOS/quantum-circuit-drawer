"""Routing helpers for layout geometry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def vertical_span(
    wire_positions: Mapping[str, float], wire_ids: Sequence[str]
) -> tuple[float, float]:
    """Return the top and bottom y positions covered by the given wires."""

    iterator = iter(wire_ids)
    first_wire_id = next(iterator)
    first_value = wire_positions[first_wire_id]
    minimum_value = first_value
    maximum_value = first_value
    for wire_id in iterator:
        wire_value = wire_positions[wire_id]
        if wire_value < minimum_value:
            minimum_value = wire_value
        if wire_value > maximum_value:
            maximum_value = wire_value
    return minimum_value, maximum_value
