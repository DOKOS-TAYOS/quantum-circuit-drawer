"""Routing helpers for layout geometry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def vertical_span(
    wire_positions: Mapping[str, float], wire_ids: Sequence[str]
) -> tuple[float, float]:
    """Return the top and bottom y positions covered by the given wires."""

    values = [wire_positions[wire_id] for wire_id in wire_ids]
    return min(values), max(values)
