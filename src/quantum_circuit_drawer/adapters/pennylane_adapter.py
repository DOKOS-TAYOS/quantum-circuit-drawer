"""PennyLane adapter with conservative MVP support."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, cast

from .._matrix_support import square_matrix
from ..exceptions import UnsupportedFrameworkError, UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ._helpers import (
    append_classical_conditions,
    build_classical_register,
    canonical_gate_spec,
    expand_operation_sequence,
    extract_dependency_types,
    is_expected_matrix_unavailable_error,
    resolve_composite_mode,
    resolve_explicit_matrices,
    sequential_bit_labels,
)
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
        tape_types = extract_dependency_types(
            "pennylane",
            ("tape.QuantumTape", "tape.QuantumScript"),
        )
        if tape_types and isinstance(circuit, tape_types):
            return True
        return any(
            _looks_like_tape(getattr(circuit, attribute, None))
            for attribute in ("qtape", "tape", "_tape")
        )

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        tape = self._extract_tape(circuit)
        composite_mode = resolve_composite_mode(options)
        explicit_matrices = resolve_explicit_matrices(options)
        wire_ids = {wire: f"q{index}" for index, wire in enumerate(tape.wires)}
        quantum_wires = [
            WireIR(id=wire_ids[wire], index=index, kind=WireKind.QUANTUM, label=str(wire))
            for index, wire in enumerate(tape.wires)
        ]

        mid_measure_operations = [
            operation for operation in tape.operations if self._is_mid_measure(operation)
        ]
        terminal_measurement_wires = tuple(
            self._terminal_measurement_wires(measurement, tape.wires)
            for measurement in tape.measurements
        )
        terminal_measurement_count = sum(len(wires) for wires in terminal_measurement_wires)
        measurement_labels = sequential_bit_labels(
            len(mid_measure_operations) + terminal_measurement_count
        )
        classical_wires, measurement_targets = build_classical_register(measurement_labels)
        mid_measure_targets = {
            self._mid_measure_id(operation): measurement_targets[index]
            for index, operation in enumerate(mid_measure_operations)
        }

        sequential_operations: list[OperationIR | MeasurementIR] = []
        for operation in tape.operations:
            sequential_operations.extend(
                self._convert_operation(
                    operation,
                    wire_ids,
                    mid_measure_targets=mid_measure_targets,
                    composite_mode=composite_mode,
                    explicit_matrices=explicit_matrices,
                )
            )

        terminal_measurement_operations: list[MeasurementIR] = []
        target_index = len(mid_measure_operations)
        for measured_wires in terminal_measurement_wires:
            for measured_wire in measured_wires:
                classical_target, classical_bit_label = measurement_targets[target_index]
                terminal_measurement_operations.append(
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=(wire_ids[measured_wire],),
                        classical_target=classical_target,
                        metadata={"classical_bit_label": classical_bit_label},
                    )
                )
                target_index += 1

        return CircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=self.pack_operations((*sequential_operations, *terminal_measurement_operations)),
            metadata={"framework": self.framework_name},
        )

    def _terminal_measurement_wires(
        self,
        measurement: _PennyLaneMeasurementLike,
        tape_wires: Sequence[object],
    ) -> tuple[object, ...]:
        return tuple(measurement.wires) or tuple(tape_wires)

    def _extract_tape(self, circuit: object) -> _PennyLaneTapeLike:
        if not self.can_handle(circuit):
            raise UnsupportedFrameworkError(
                "PennyLane support in v0.1 expects a QuantumTape/QuantumScript or an object exposing .qtape/.tape"
            )
        for attribute in ("qtape", "tape", "_tape"):
            tape = getattr(circuit, attribute, None)
            if _looks_like_tape(tape):
                return cast(_PennyLaneTapeLike, tape)
        if _looks_like_tape(circuit):
            return cast(_PennyLaneTapeLike, circuit)
        raise UnsupportedFrameworkError(
            "PennyLane support in v0.1 expects a QuantumTape/QuantumScript or an object exposing .qtape/.tape"
        )

    def _convert_operation(
        self,
        operation: _PennyLaneOperationLike,
        wire_ids: dict[object, str],
        *,
        mid_measure_targets: dict[str, tuple[str, str]],
        composite_mode: str,
        explicit_matrices: bool,
    ) -> list[OperationIR | MeasurementIR]:
        if self._is_mid_measure(operation):
            if not operation.wires:
                raise UnsupportedOperationError(
                    "PennyLane mid-measurement operation has no quantum target"
                )
            measurement_id = self._mid_measure_id(operation)
            classical_target, classical_bit_label = mid_measure_targets[measurement_id]
            return [
                MeasurementIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=(wire_ids[operation.wires[0]],),
                    classical_target=classical_target,
                    metadata={"classical_bit_label": classical_bit_label},
                )
            ]

        if self._is_conditional(operation):
            base_operation = cast(_PennyLaneOperationLike, getattr(operation, "base"))
            condition = self._condition_from_measurement_value(
                getattr(operation, "meas_val"),
                mid_measure_targets,
            )
            converted_base = self._convert_operation(
                base_operation,
                wire_ids,
                mid_measure_targets=mid_measure_targets,
                composite_mode=composite_mode,
                explicit_matrices=explicit_matrices,
            )
            return [append_classical_conditions(node, (condition,)) for node in converted_base]

        canonical_gate = canonical_gate_spec(
            getattr(operation, "name", operation.__class__.__name__)
        )
        if composite_mode == "expand" and canonical_gate.family is CanonicalGateFamily.CUSTOM:
            decomposition = self._decomposition(operation)
            if decomposition:
                return expand_operation_sequence(
                    decomposition,
                    lambda nested_operation: self._convert_operation(
                        cast(_PennyLaneOperationLike, nested_operation),
                        wire_ids,
                        mid_measure_targets=mid_measure_targets,
                        composite_mode=composite_mode,
                        explicit_matrices=explicit_matrices,
                    ),
                )

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

        parameters = tuple(getattr(operation, "parameters", ()) or ())
        if canonical_gate.label == "SWAP":
            return [OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=target_wires)]
        if canonical_gate.label == "BARRIER":
            return [
                OperationIR(
                    kind=OperationKind.BARRIER,
                    name="BARRIER",
                    target_wires=target_wires,
                )
            ]
        if control_wires:
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=canonical_gate.label,
                    canonical_family=canonical_gate.family,
                    target_wires=target_wires,
                    control_wires=control_wires,
                    parameters=parameters,
                    metadata=self._matrix_metadata(
                        operation,
                        explicit_matrices=explicit_matrices,
                    ),
                )
            ]
        return [
            OperationIR(
                kind=OperationKind.GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=target_wires,
                parameters=parameters,
                metadata=self._matrix_metadata(
                    operation,
                    explicit_matrices=explicit_matrices,
                ),
            )
        ]

    def _is_mid_measure(self, operation: object) -> bool:
        return getattr(operation, "name", None) == "MidMeasureMP"

    def _mid_measure_id(self, operation: object) -> str:
        measurement_id = getattr(operation, "id", None)
        if measurement_id is not None:
            return str(measurement_id)
        hyperparameters = getattr(operation, "hyperparameters", {}) or {}
        return str(hyperparameters.get("id"))

    def _is_conditional(self, operation: object) -> bool:
        return hasattr(operation, "meas_val") and hasattr(operation, "base")

    def _condition_from_measurement_value(
        self,
        measurement_value: object,
        mid_measure_targets: dict[str, tuple[str, str]],
    ) -> ClassicalConditionIR:
        measurements = tuple(getattr(measurement_value, "measurements", ()) or ())
        branches = dict(getattr(measurement_value, "branches", {}) or {})
        matching_branch = next(
            (branch_bits for branch_bits, branch_value in branches.items() if bool(branch_value)),
            None,
        )
        if matching_branch is None:
            matching_branch = next(iter(branches), ())
        branch_bits = tuple(matching_branch)
        wire_targets = [
            mid_measure_targets[self._mid_measure_id(measurement)] for measurement in measurements
        ]
        wire_ids = tuple(dict.fromkeys(wire_id for wire_id, _ in wire_targets))
        if len(wire_targets) == 1 and len(branch_bits) == 1:
            _, bit_label = wire_targets[0]
            expression = f"if {bit_label}={branch_bits[0]}"
        else:
            integer_value = 0
            for bit in branch_bits:
                integer_value = (integer_value << 1) | int(bit)
            expression = f"if c={integer_value}"
        return ClassicalConditionIR(wire_ids=wire_ids, expression=expression)

    def _decomposition(self, operation: object) -> tuple[object, ...]:
        if not bool(getattr(operation, "has_decomposition", False)):
            return ()
        decomposition = getattr(operation, "decomposition", None)
        if callable(decomposition):
            return tuple(decomposition())
        return ()

    def _matrix_metadata(
        self,
        operation: object,
        *,
        explicit_matrices: bool = True,
    ) -> dict[str, object]:
        if not explicit_matrices:
            return {}

        direct_matrix = getattr(operation, "matrix", None)
        if direct_matrix is not None:
            if callable(direct_matrix):
                try:
                    direct_matrix = direct_matrix()
                except Exception as exc:
                    if not is_expected_matrix_unavailable_error(exc):
                        raise
                    direct_matrix = None
            if direct_matrix is not None and square_matrix(direct_matrix) is not None:
                return {"matrix": direct_matrix}

        try:
            import pennylane as qml
        except ImportError:
            return {}

        matrix_function = getattr(qml, "matrix", None)
        if not callable(matrix_function):
            return {}

        try:
            matrix = matrix_function(operation)
        except Exception as exc:
            if not is_expected_matrix_unavailable_error(exc):
                raise
            return {}

        if square_matrix(matrix) is None:
            return {}
        return {"matrix": matrix}


def _looks_like_tape(candidate: object | None) -> bool:
    if candidate is None:
        return False
    return all(
        hasattr(candidate, attribute) for attribute in ("wires", "operations", "measurements")
    )
