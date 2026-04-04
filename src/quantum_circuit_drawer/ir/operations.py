"""Operation-level intermediate representation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from ..typing import Metadata


class OperationKind(str, Enum):
    """Supported operation categories."""

    GATE = "gate"
    CONTROLLED_GATE = "controlled_gate"
    SWAP = "swap"
    BARRIER = "barrier"
    MEASUREMENT = "measurement"


def _normalize_wire_ids(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


def _normalize_parameters(values: Sequence[object]) -> tuple[object, ...]:
    return tuple(values)


@dataclass(slots=True)
class OperationIR:
    """Neutral operation description."""

    kind: OperationKind
    name: str
    target_wires: Sequence[str]
    control_wires: Sequence[str] = field(default_factory=tuple)
    parameters: Sequence[object] = field(default_factory=tuple)
    label: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.target_wires = _normalize_wire_ids(self.target_wires)
        self.control_wires = _normalize_wire_ids(self.control_wires)
        self.parameters = _normalize_parameters(self.parameters)
        if not self.name:
            raise ValueError("operation name cannot be empty")
        if not self.target_wires and self.kind is not OperationKind.BARRIER:
            raise ValueError("operation must reference at least one target wire")
        if self.label is None:
            self.label = self.name

    @property
    def occupied_wire_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.control_wires, *self.target_wires)))
