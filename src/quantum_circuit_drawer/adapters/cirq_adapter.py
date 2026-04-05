"""Cirq adapter."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from math import isclose
from typing import Any, Protocol, cast

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ._helpers import (
    CanonicalGateSpec,
    build_classical_register,
    canonical_gate_spec,
    extract_dependency_types,
    sequential_bit_labels,
)
from .base import BaseAdapter


class _CirqOperationLike(Protocol):
    qubits: Sequence[object]


class _CirqMomentLike(Protocol):
    operations: Sequence[_CirqOperationLike]


class _CirqCircuitLike(Protocol):
    def all_qubits(self) -> Iterable[object]: ...

    def __iter__(self) -> Iterator[_CirqMomentLike]: ...


class CirqAdapter(BaseAdapter):
    """Convert cirq.Circuit objects into CircuitIR."""

    framework_name = "cirq"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        circuit_types = extract_dependency_types("cirq", ("Circuit",))
        return bool(circuit_types) and isinstance(circuit, circuit_types)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("CirqAdapter received a non-Cirq circuit")

        import cirq

        typed_circuit = cast(_CirqCircuitLike, circuit)
        qubits = sorted(typed_circuit.all_qubits(), key=str)
        qubit_ids = {qubit: f"q{index}" for index, qubit in enumerate(qubits)}
        quantum_wires = [
            WireIR(id=qubit_ids[qubit], index=index, kind=WireKind.QUANTUM, label=str(qubit))
            for index, qubit in enumerate(qubits)
        ]

        measurement_slots: dict[tuple[int, int, int], tuple[str, str]] = {}
        measurement_labels: list[str] = []
        for moment_index, moment in enumerate(typed_circuit):
            for operation_index, operation in enumerate(moment.operations):
                if self._is_measurement(operation):
                    for slot_index, _ in enumerate(operation.qubits):
                        measurement_labels.append(f"c[{len(measurement_labels)}]")
                        measurement_slots[(moment_index, operation_index, slot_index)] = (
                            "c0",
                            measurement_labels[-1],
                        )

        classical_wires, _ = build_classical_register(
            sequential_bit_labels(len(measurement_labels))
        )

        layers: list[LayerIR] = []
        for moment_index, moment in enumerate(typed_circuit):
            operations: list[OperationIR | MeasurementIR] = []
            for operation_index, operation in enumerate(moment.operations):
                operations.extend(
                    self._convert_operation(
                        cirq=cirq,
                        operation=operation,
                        qubit_ids=qubit_ids,
                        measurement_slots=measurement_slots,
                        operation_key=(moment_index, operation_index),
                    )
                )
            layers.append(LayerIR(operations=operations))

        return CircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=layers,
            metadata={"framework": self.framework_name},
        )

    def _convert_operation(
        self,
        *,
        cirq: Any,
        operation: _CirqOperationLike,
        qubit_ids: dict[object, str],
        measurement_slots: dict[tuple[int, int, int], tuple[str, str]],
        operation_key: tuple[int, int],
    ) -> list[OperationIR | MeasurementIR]:
        if self._is_measurement(operation):
            converted: list[OperationIR | MeasurementIR] = []
            for slot_index, qubit in enumerate(operation.qubits):
                classical_target, classical_bit_label = measurement_slots[
                    (*operation_key, slot_index)
                ]
                converted.append(
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=(qubit_ids[qubit],),
                        classical_target=classical_target,
                        metadata={"classical_bit_label": classical_bit_label},
                    )
                )
            return converted

        gate = getattr(operation, "gate", None)
        class_name = (
            gate.__class__.__name__.lower()
            if gate is not None
            else operation.__class__.__name__.lower()
        )
        target_wires = tuple(qubit_ids[qubit] for qubit in operation.qubits)

        if isinstance(operation, cirq.ControlledOperation):
            controlled_operation = cast(Any, operation)
            controls = tuple(qubit_ids[qubit] for qubit in controlled_operation.controls)
            targets = tuple(qubit_ids[qubit] for qubit in controlled_operation.sub_operation.qubits)
            canonical_gate, parameters = self._canonical_gate_for_operation(
                controlled_operation.sub_operation
            )
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=canonical_gate.label,
                    canonical_family=canonical_gate.family,
                    target_wires=targets,
                    control_wires=controls,
                    parameters=parameters,
                )
            ]

        if class_name in {"cxpowgate", "cnotpowgate", "ccxpowgate"}:
            control_count = (
                1 if class_name in {"cxpowgate", "cnotpowgate"} else len(target_wires) - 1
            )
            canonical_gate = canonical_gate_spec("CNOT" if control_count == 1 else "TOFFOLI")
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=canonical_gate.label,
                    canonical_family=canonical_gate.family,
                    target_wires=(target_wires[-1],),
                    control_wires=target_wires[:control_count],
                    parameters=self._extract_parameters(gate),
                )
            ]
        if class_name == "czpowgate":
            canonical_gate = canonical_gate_spec("CZ")
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=canonical_gate.label,
                    canonical_family=canonical_gate.family,
                    target_wires=(target_wires[1],),
                    control_wires=(target_wires[0],),
                    parameters=self._extract_parameters(gate),
                )
            ]
        if class_name == "swappowgate":
            return [OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=target_wires)]

        canonical_gate, parameters = self._canonical_gate_for_operation(operation)
        return [
            OperationIR(
                kind=OperationKind.GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=target_wires,
                parameters=parameters,
            )
        ]

    def _is_measurement(self, operation: object) -> bool:
        gate = getattr(operation, "gate", None)
        return gate is not None and gate.__class__.__name__ == "MeasurementGate"

    def _canonical_gate_for_operation(
        self, operation: object
    ) -> tuple[CanonicalGateSpec, tuple[object, ...]]:
        gate = getattr(operation, "gate", None)
        if gate is None:
            return canonical_gate_spec(operation.__class__.__name__), ()

        special_label = self._special_canonical_label(gate)
        if special_label is not None:
            return canonical_gate_spec(special_label), ()

        return canonical_gate_spec(self._raw_operation_name(operation)), self._extract_parameters(gate)

    def _special_canonical_label(self, gate: object) -> str | None:
        exponent = getattr(gate, "exponent", None)
        if exponent is None:
            return None
        try:
            exponent_value = float(exponent)
        except (TypeError, ValueError):
            return None

        class_name = gate.__class__.__name__.lower()
        if class_name == "xpowgate":
            if isclose(exponent_value, 0.5, rel_tol=0.0, abs_tol=1e-9):
                return "SX"
            if isclose(exponent_value, -0.5, rel_tol=0.0, abs_tol=1e-9):
                return "SXdg"
            return None

        if class_name == "zpowgate":
            special_labels = {
                0.5: "S",
                -0.5: "Sdg",
                0.25: "T",
                -0.25: "Tdg",
            }
            for special_exponent, label in special_labels.items():
                if isclose(exponent_value, special_exponent, rel_tol=0.0, abs_tol=1e-9):
                    return label
        return None

    def _raw_operation_name(self, operation: object) -> str:
        gate = getattr(operation, "gate", None)
        if gate is None:
            return operation.__class__.__name__
        class_name = gate.__class__.__name__.lower()
        mapping = {
            "hpowgate": "H",
            "xpowgate": "X",
            "ypowgate": "Y",
            "zpowgate": "Z",
            "cnotpowgate": "CNOT",
            "cxpowgate": "CX",
            "ccxpowgate": "TOFFOLI",
            "czpowgate": "CZ",
            "swappowgate": "SWAP",
            "iswappowgate": "iSWAP",
        }
        return mapping.get(class_name, str(gate))

    def _extract_parameters(self, gate: object) -> tuple[object, ...]:
        if gate is None:
            return ()
        values: list[object] = []
        for attribute in ("theta", "phi", "lam", "exponent"):
            if not hasattr(gate, attribute):
                continue
            value = getattr(gate, attribute)
            if attribute == "exponent" and value == 1:
                continue
            values.append(value)
        return tuple(values)