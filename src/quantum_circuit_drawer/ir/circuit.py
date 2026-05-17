"""Circuit-level intermediate representation used across the drawing pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ..typing import Metadata
from .measurements import MeasurementIR
from .operations import OperationIR
from .wires import WireIR, WireKind

OperationNode = OperationIR | MeasurementIR


@dataclass(slots=True)
class LayerIR:
    """One drawable time step in a ``CircuitIR``.

    Attributes:
        operations: Operation and measurement nodes that can be drawn in the same layer
            without occupying the same wire slot.
        metadata: Optional framework or adapter metadata. The renderer preserves it but
            does not require any specific keys.
    """

    operations: Sequence[OperationNode] = field(default_factory=tuple)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.operations = tuple(self.operations)


@dataclass(slots=True)
class CircuitIR:
    """Framework-neutral circuit model accepted by the public draw APIs.

    Attributes:
        quantum_wires: Ordered quantum wires. Wire ids must be unique across quantum and
            classical wires.
        classical_wires: Ordered classical wires used by measurements and conditions.
        layers: Ordered ``LayerIR`` objects. Each layer represents one drawable time
            step after packing operations.
        name: Optional circuit name.
        metadata: Optional framework or adapter metadata. Common keys include
            ``"framework"`` and diagnostics-related provenance.

    Quantum and classical wires share one identifier space so layout, routing, and
    annotation code can reason about every occupied slot consistently.
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
        _validate_wire_group_kinds(self.quantum_wires, self.classical_wires)
        wire_ids = [wire.id for wire in self.all_wires]
        if len(wire_ids) != len(set(wire_ids)):
            raise ValueError("wire ids must be unique across quantum and classical wires")
        wire_map = {wire.id: wire for wire in self.all_wires}
        _validate_operation_wire_references(self.layers, known_wire_ids=set(wire_ids))
        _validate_operation_wire_kinds(self.layers, wire_map=wire_map)

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


def _validate_wire_group_kinds(
    quantum_wires: tuple[WireIR, ...],
    classical_wires: tuple[WireIR, ...],
) -> None:
    if any(wire.kind is not WireKind.QUANTUM for wire in quantum_wires):
        raise ValueError("quantum_wires must contain only quantum wires")
    if any(wire.kind is not WireKind.CLASSICAL for wire in classical_wires):
        raise ValueError("classical_wires must contain only classical wires")


def _validate_operation_wire_references(
    layers: tuple[LayerIR, ...],
    *,
    known_wire_ids: set[str],
) -> None:
    for layer in layers:
        for operation in layer.operations:
            for wire_id in operation.occupied_wire_ids:
                if wire_id not in known_wire_ids:
                    raise ValueError(f"operation references unknown wire id {wire_id!r}")


def _validate_operation_wire_kinds(
    layers: tuple[LayerIR, ...],
    *,
    wire_map: dict[str, WireIR],
) -> None:
    for layer in layers:
        for operation in layer.operations:
            _validate_wire_ids_have_kind(
                operation.control_wires,
                wire_map=wire_map,
                expected_kind=WireKind.QUANTUM,
                message="operation control_wires must reference quantum wire ids",
            )
            for condition in operation.classical_conditions:
                _validate_wire_ids_have_kind(
                    condition.wire_ids,
                    wire_map=wire_map,
                    expected_kind=WireKind.CLASSICAL,
                    message="classical condition wire_ids must reference classical wire ids",
                )
            if isinstance(operation, MeasurementIR):
                _validate_wire_ids_have_kind(
                    operation.target_wires,
                    wire_map=wire_map,
                    expected_kind=WireKind.QUANTUM,
                    message="measurement target_wires must reference quantum wire ids",
                )
                _validate_wire_ids_have_kind(
                    (operation.classical_target,),
                    wire_map=wire_map,
                    expected_kind=WireKind.CLASSICAL,
                    message="measurement classical_target must reference a classical wire id",
                )


def _validate_wire_ids_have_kind(
    wire_ids: Sequence[str | None],
    *,
    wire_map: dict[str, WireIR],
    expected_kind: WireKind,
    message: str,
) -> None:
    if any(wire_id is None or wire_map[wire_id].kind is not expected_kind for wire_id in wire_ids):
        raise ValueError(message)
