"""Circuit-level intermediate representation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ..typing import Metadata
from .measurements import MeasurementIR
from .operations import OperationIR
from .wires import WireIR

OperationNode = OperationIR | MeasurementIR


@dataclass(slots=True)
class LayerIR:
    """A drawable circuit layer."""

    operations: Sequence[OperationNode] = field(default_factory=tuple)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.operations = tuple(self.operations)


@dataclass(slots=True)
class CircuitIR:
    """Framework-neutral circuit model."""

    quantum_wires: Sequence[WireIR]
    classical_wires: Sequence[WireIR] = field(default_factory=tuple)
    layers: Sequence[LayerIR] = field(default_factory=tuple)
    name: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.quantum_wires = tuple(self.quantum_wires)
        self.classical_wires = tuple(self.classical_wires)
        self.layers = tuple(self.layers)
        wire_ids = [wire.id for wire in self.all_wires]
        if len(wire_ids) != len(set(wire_ids)):
            raise ValueError("wire ids must be unique across quantum and classical wires")

    @property
    def all_wires(self) -> tuple[WireIR, ...]:
        return tuple((*self.quantum_wires, *self.classical_wires))

    @property
    def wire_map(self) -> dict[str, WireIR]:
        return {wire.id: wire for wire in self.all_wires}

    @property
    def quantum_wire_count(self) -> int:
        return len(self.quantum_wires)

    @property
    def classical_wire_count(self) -> int:
        return len(self.classical_wires)

    @property
    def total_wire_count(self) -> int:
        return len(self.all_wires)
