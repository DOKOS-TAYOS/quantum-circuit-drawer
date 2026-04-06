"""Classical-condition intermediate representation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ..typing import Metadata


def _normalize_wire_ids(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


@dataclass(frozen=True, slots=True)
class ClassicalConditionIR:
    """Neutral description of a classical condition attached to an operation."""

    wire_ids: Sequence[str]
    expression: str
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_wire_ids = _normalize_wire_ids(self.wire_ids)
        object.__setattr__(self, "wire_ids", normalized_wire_ids)
        if not self.expression.strip():
            raise ValueError("classical condition expression cannot be empty")
