"""Shared helpers for routing classical condition annotations."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from ..ir.classical_conditions import ClassicalConditionIR


@dataclass(frozen=True, slots=True)
class ClassicalConditionAnchor:
    """A single classical-wire anchor used while drawing conditions."""

    wire_id: str
    label: str | None


def iter_classical_condition_anchors(
    conditions: Sequence[ClassicalConditionIR],
) -> Iterator[ClassicalConditionAnchor]:
    """Yield classical condition anchors while labeling only the first wire per condition."""

    for condition in conditions:
        for condition_index, wire_id in enumerate(condition.wire_ids):
            yield ClassicalConditionAnchor(
                wire_id=wire_id,
                label=condition.expression if condition_index == 0 else None,
            )
