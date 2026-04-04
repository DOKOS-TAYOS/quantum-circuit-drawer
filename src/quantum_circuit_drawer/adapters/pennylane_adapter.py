"""PennyLane adapter with conservative MVP support."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, cast

from ..exceptions import UnsupportedFrameworkError
from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ..utils.formatting import format_gate_name
from .base import BaseAdapter


class _PennyLaneOperationLike(Protocol):
    wires: Sequence[object]
    name: str
    parameters: Sequence[object]


class _PennyLaneMeasurementLike(Protocol):
    wires: Sequence[object]


class _PennyLaneTapeLike(Protocol):
    wires: Sequence[object]
    operations: Sequence[_PennyLaneOperationLike]
    measurements: Sequence[_PennyLaneMeasurementLike]


class PennyLaneAdapter(BaseAdapter):
    """Convert tape-like PennyLane objects into CircuitIR."""

    framework_name = "pennylane"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        try:
            import pennylane as qml
        except ImportError:
            return False

        tape_types = tuple(
            candidate
            for candidate in (
                getattr(getattr(qml, "tape", None), "QuantumTape", None),
                getattr(getattr(qml, "tape", None), "QuantumScript", None),
            )
            if candidate is not None
        )
        if tape_types and isinstance(circuit, tape_types):
            return True
        return any(
            getattr(circuit, attribute, None) is not None
            for attribute in ("qtape", "tape", "_tape")
        )

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        tape = self._extract_tape(circuit)
        wire_ids = {wire: f"q{index}" for index, wire in enumerate(tape.wires)}
        quantum_wires = [
            WireIR(id=wire_ids[wire], index=index, kind=WireKind.QUANTUM, label=str(wire))
            for index, wire in enumerate(tape.wires)
        ]

        sequential_operations = [
            self._convert_operation(operation, wire_ids) for operation in tape.operations
        ]
        layers = list(self.pack_operations(sequential_operations))

        classical_wires: list[WireIR] = []
        measurement_operations: list[MeasurementIR] = []
        if tape.measurements:
            classical_wires.append(
                WireIR(
                    id="c0",
                    index=0,
                    kind=WireKind.CLASSICAL,
                    label="c",
                    metadata={"bundle_size": len(tape.measurements)},
                )
            )
        for measurement_index, measurement in enumerate(tape.measurements):
            measured_wires = tuple(wire_ids[wire] for wire in measurement.wires) or tuple(
                wire.id for wire in quantum_wires
            )
            measurement_operations.append(
                MeasurementIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=(measured_wires[0],),
                    classical_target="c0",
                    metadata={"classical_bit_label": f"c[{measurement_index}]"},
                )
            )
        if measurement_operations:
            layers.append(LayerIR(operations=measurement_operations))

        return CircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=tuple(layers),
            metadata={"framework": self.framework_name},
        )

    def _extract_tape(self, circuit: object) -> _PennyLaneTapeLike:
        if not self.can_handle(circuit):
            raise UnsupportedFrameworkError(
                "PennyLane support in v0.1 expects a QuantumTape/QuantumScript or an object exposing .qtape/.tape"
            )
        for attribute in ("qtape", "tape", "_tape"):
            tape = getattr(circuit, attribute, None)
            if tape is not None:
                return cast(_PennyLaneTapeLike, tape)
        return cast(_PennyLaneTapeLike, circuit)

    def _convert_operation(
        self, operation: _PennyLaneOperationLike, wire_ids: dict[object, str]
    ) -> OperationIR:
        control_wires = tuple(
            wire_ids[wire] for wire in getattr(operation, "control_wires", ()) if wire in wire_ids
        )
        target_candidates = getattr(operation, "target_wires", None)
        if target_candidates is None:
            target_wires = tuple(
                wire_ids[wire] for wire in operation.wires if wire_ids[wire] not in control_wires
            )
        else:
            target_wires = tuple(wire_ids[wire] for wire in target_candidates)

        if not target_wires:
            target_wires = tuple(wire_ids[wire] for wire in operation.wires)

        name = format_gate_name(getattr(operation, "name", operation.__class__.__name__))
        parameters = tuple(getattr(operation, "parameters", ()) or ())
        if name == "SWAP":
            return OperationIR(kind=OperationKind.SWAP, name=name, target_wires=target_wires)
        if name == "BARRIER":
            return OperationIR(kind=OperationKind.BARRIER, name=name, target_wires=target_wires)
        if control_wires:
            return OperationIR(
                kind=OperationKind.CONTROLLED_GATE,
                name=name,
                target_wires=target_wires,
                control_wires=control_wires,
                parameters=parameters,
            )
        return OperationIR(
            kind=OperationKind.GATE, name=name, target_wires=target_wires, parameters=parameters
        )
