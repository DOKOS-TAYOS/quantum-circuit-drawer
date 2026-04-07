"""Circuit-level intermediate representation used across the drawing pipeline."""

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
    """A drawable circuit layer containing operations that share one time step."""

    operations: Sequence[OperationNode] = field(default_factory=tuple)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.operations = tuple(self.operations)


@dataclass(slots=True)
class CircuitIR:
    """Framework-neutral circuit model consumed by layout engines.

    Quantum and classical wires live in one shared identifier space so layout,
    routing, and annotation code can reason about every occupied slot in a
    consistent way.
    """

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
        """Return quantum wires followed by classical wires."""

        return tuple((*self.quantum_wires, *self.classical_wires))

    @property
    def wire_map(self) -> dict[str, WireIR]:
        """Return the wires keyed by their unique wire id."""

        return {wire.id: wire for wire in self.all_wires}

    @property
    def quantum_wire_count(self) -> int:
        """Return the number of quantum wires."""

        return len(self.quantum_wires)

    @property
    def classical_wire_count(self) -> int:
        """Return the number of classical wires."""

        return len(self.classical_wires)

    @property
    def total_wire_count(self) -> int:
        """Return the total number of quantum and classical wires."""

        return len(self.all_wires)
