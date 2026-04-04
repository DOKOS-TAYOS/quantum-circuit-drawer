"""Cirq adapter."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from typing import Any, Protocol, cast

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ..utils.formatting import format_gate_name
from .base import BaseAdapter


class _CirqOperationLike(Protocol):
    qubits: Sequence[object]


class _CirqMomentLike(Protocol):
    operations: Sequence[_CirqOperationLike]


class _CirqCircuitLike(Protocol):
    def all_qubits(self) -> Iterable[object]:
        ...

    def __iter__(self) -> Iterator[_CirqMomentLike]:
        ...


class CirqAdapter(BaseAdapter):
    """Convert cirq.Circuit objects into CircuitIR."""

    framework_name = "cirq"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        try:
            import cirq
        except ImportError:
            return False
        return isinstance(circuit, cirq.Circuit)

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
        measurement_slot_count = 0
        for moment_index, moment in enumerate(typed_circuit):
            for operation_index, operation in enumerate(moment.operations):
                if self._is_measurement(operation):
                    for slot_index, _ in enumerate(operation.qubits):
                        measurement_slots[(moment_index, operation_index, slot_index)] = (
                            "c0",
                            f"c[{measurement_slot_count}]",
                        )
                        measurement_slot_count += 1

        classical_wires: list[WireIR] = []
        if measurement_slot_count:
            classical_wires.append(
                WireIR(
                    id="c0",
                    index=0,
                    kind=WireKind.CLASSICAL,
                    label="c",
                    metadata={"bundle_size": measurement_slot_count},
                )
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
        parameters = self._extract_parameters(gate)

        if isinstance(operation, cirq.ControlledOperation):
            controlled_operation = cast(Any, operation)
            controls = tuple(qubit_ids[qubit] for qubit in controlled_operation.controls)
            targets = tuple(qubit_ids[qubit] for qubit in controlled_operation.sub_operation.qubits)
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=self._operation_name(controlled_operation.sub_operation),
                    target_wires=targets,
                    control_wires=controls,
                    parameters=self._extract_parameters(controlled_operation.sub_operation.gate),
                )
            ]

        if class_name in {"cxpowgate", "cnotpowgate"}:
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name="X",
                    target_wires=(target_wires[1],),
                    control_wires=(target_wires[0],),
                    parameters=parameters,
                )
            ]
        if class_name == "czpowgate":
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name="Z",
                    target_wires=(target_wires[1],),
                    control_wires=(target_wires[0],),
                    parameters=parameters,
                )
            ]
        if class_name == "swappowgate":
            return [OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=target_wires)]

        return [
            OperationIR(
                kind=OperationKind.GATE,
                name=self._operation_name(operation),
                target_wires=target_wires,
                parameters=parameters,
            )
        ]

    def _is_measurement(self, operation: object) -> bool:
        gate = getattr(operation, "gate", None)
        return gate is not None and gate.__class__.__name__ == "MeasurementGate"

    def _operation_name(self, operation: object) -> str:
        gate = getattr(operation, "gate", None)
        if gate is None:
            return format_gate_name(operation.__class__.__name__)
        class_name = gate.__class__.__name__.lower()
        mapping = {
            "hpowgate": "H",
            "xpowgate": "X",
            "ypowgate": "Y",
            "zpowgate": "Z",
            "cnotpowgate": "X",
            "cxpowgate": "X",
            "czpowgate": "Z",
            "swappowgate": "SWAP",
        }
        return mapping.get(class_name, format_gate_name(str(gate)))

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
