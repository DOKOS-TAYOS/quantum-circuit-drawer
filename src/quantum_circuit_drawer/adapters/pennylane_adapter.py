"""PennyLane adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from inspect import getattr_static
from typing import Protocol, cast

from ..exceptions import UnsupportedFrameworkError, UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.operations import CanonicalGateFamily, OperationKind
from ..ir.semantic import SemanticCircuitIR, SemanticOperationIR, pack_semantic_operations
from ..ir.wires import WireIR, WireKind
from ..utils.matrix_support import square_matrix
from ._helpers import (
    append_semantic_classical_conditions,
    build_classical_register,
    canonical_gate_spec,
    expand_operation_sequence,
    extract_dependency_types,
    is_expected_matrix_unavailable_error,
    normalized_detail_lines,
    resolve_composite_mode,
    resolve_explicit_matrices,
    resolve_wire_ids,
    semantic_provenance,
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


_TERMINAL_LABEL_BY_KIND: dict[str, str] = {
    "expval": "EXPVAL",
    "var": "VAR",
    "probs": "PROBS",
    "sample": "SAMPLE",
    "counts": "COUNTS",
    "state": "STATE",
    "density_matrix": "DM",
}
_TENSOR_OBSERVABLE_NAMES = frozenset({"prod", "tensor"})
_OBSERVABLE_SUMMARY_LIMIT = 24


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
        return any(_looks_like_tape(tape) for tape in _safe_wrapped_tape_candidates(circuit))

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        semantic_ir = self.to_semantic_ir(circuit, options=options)
        assert semantic_ir is not None
        return lower_semantic_circuit(semantic_ir)

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR:
        tape = self._extract_tape(circuit)
        composite_mode = resolve_composite_mode(options)
        explicit_matrices = resolve_explicit_matrices(options)
        wire_ids = resolve_wire_ids(tuple(tape.wires), prefix="q")
        wire_labels = {wire: str(wire) for wire in tape.wires}
        quantum_wires = [
            WireIR(id=wire_ids[wire], index=index, kind=WireKind.QUANTUM, label=str(wire))
            for index, wire in enumerate(tape.wires)
        ]

        mid_measure_operations = [
            operation for operation in tape.operations if self._is_mid_measure(operation)
        ]
        measurement_labels = sequential_bit_labels(len(mid_measure_operations))
        classical_wires, measurement_targets = build_classical_register(measurement_labels)
        mid_measure_targets = {
            self._mid_measure_id(operation): measurement_targets[index]
            for index, operation in enumerate(mid_measure_operations)
        }

        semantic_operations: list[SemanticOperationIR] = []
        for operation in tape.operations:
            semantic_operations.extend(
                self._convert_operation(
                    operation,
                    wire_ids,
                    mid_measure_targets=mid_measure_targets,
                    composite_mode=composite_mode,
                    explicit_matrices=explicit_matrices,
                )
            )

        terminal_measurement_operations: list[SemanticOperationIR] = []
        for measurement_index, measurement in enumerate(tape.measurements):
            terminal_measurement_operations.append(
                self._convert_terminal_measurement(
                    measurement,
                    tape_wires=tuple(tape.wires),
                    wire_ids=wire_ids,
                    wire_labels=wire_labels,
                    location=(measurement_index,),
                )
            )

        return SemanticCircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=(
                *pack_semantic_operations(semantic_operations),
                *pack_semantic_operations(terminal_measurement_operations),
            ),
            metadata={"framework": self.framework_name},
        )

    def _extract_tape(self, circuit: object) -> _PennyLaneTapeLike:
        if _looks_like_tape(circuit):
            return cast(_PennyLaneTapeLike, circuit)
        for tape in _safe_wrapped_tape_candidates(circuit):
            if _looks_like_tape(tape):
                return cast(_PennyLaneTapeLike, tape)
        raise UnsupportedFrameworkError(
            "PennyLane support expects a QuantumTape/QuantumScript or a wrapper exposing a materialized .qtape, .tape, or ._tape"
        )

    def _convert_operation(
        self,
        operation: _PennyLaneOperationLike,
        wire_ids: dict[object, str],
        *,
        mid_measure_targets: dict[str, tuple[str, str]],
        composite_mode: str,
        explicit_matrices: bool,
        decomposition_origin: str | None = None,
    ) -> list[SemanticOperationIR]:
        if self._is_mid_measure(operation):
            if not operation.wires:
                raise UnsupportedOperationError(
                    "PennyLane mid-measurement operation has no quantum target"
                )
            measurement_id = self._mid_measure_id(operation)
            classical_target, classical_bit_label = mid_measure_targets[measurement_id]
            return [
                SemanticOperationIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=(wire_ids[operation.wires[0]],),
                    classical_target=classical_target,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name="MidMeasureMP",
                        native_kind="measurement",
                        location=(0,),
                    ),
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
                decomposition_origin=decomposition_origin,
            )
            return [
                replace(
                    append_semantic_classical_conditions(node, (condition,)),
                    hover_details=(
                        *node.hover_details,
                        *normalized_detail_lines(f"conditional on: {condition.expression}"),
                    ),
                )
                for node in converted_base
            ]

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
                        decomposition_origin=getattr(
                            operation, "name", operation.__class__.__name__
                        ),
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
            return [
                SemanticOperationIR(
                    kind=OperationKind.SWAP,
                    name="SWAP",
                    target_wires=target_wires,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=getattr(operation, "name", operation.__class__.__name__),
                        native_kind="swap",
                        decomposition_origin=decomposition_origin,
                    ),
                )
            ]
        if canonical_gate.label == "BARRIER":
            return [
                SemanticOperationIR(
                    kind=OperationKind.BARRIER,
                    name="BARRIER",
                    target_wires=target_wires,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=getattr(operation, "name", operation.__class__.__name__),
                        native_kind="barrier",
                        decomposition_origin=decomposition_origin,
                    ),
                )
            ]
        if control_wires:
            return [
                SemanticOperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=canonical_gate.label,
                    canonical_family=canonical_gate.family,
                    target_wires=target_wires,
                    control_wires=control_wires,
                    parameters=parameters,
                    hover_details=normalized_detail_lines(
                        f"decomposed from: {decomposition_origin}"
                        if decomposition_origin is not None
                        else None
                    ),
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=getattr(operation, "name", operation.__class__.__name__),
                        native_kind="controlled_gate",
                        decomposition_origin=decomposition_origin,
                    ),
                    metadata=self._matrix_metadata(
                        operation,
                        explicit_matrices=explicit_matrices,
                    ),
                )
            ]
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=target_wires,
                parameters=parameters,
                hover_details=normalized_detail_lines(
                    f"decomposed from: {decomposition_origin}"
                    if decomposition_origin is not None
                    else None
                ),
                provenance=semantic_provenance(
                    framework=self.framework_name,
                    native_name=getattr(operation, "name", operation.__class__.__name__),
                    native_kind="gate",
                    decomposition_origin=decomposition_origin,
                ),
                metadata=self._matrix_metadata(
                    operation,
                    explicit_matrices=explicit_matrices,
                ),
            )
        ]

    def _convert_terminal_measurement(
        self,
        measurement: _PennyLaneMeasurementLike,
        *,
        tape_wires: Sequence[object],
        wire_ids: Mapping[object, str],
        wire_labels: Mapping[object, str],
        location: Sequence[int],
    ) -> SemanticOperationIR:
        terminal_kind = self._terminal_measurement_kind(measurement)
        if terminal_kind is None:
            raise UnsupportedOperationError(
                "PennyLane terminal measurement type "
                f"{measurement.__class__.__name__} is not currently supported for drawing"
            )

        target_native_wires = self._terminal_measurement_targets(
            measurement,
            tape_wires=tape_wires,
        )
        target_wires = tuple(wire_ids[wire] for wire in target_native_wires)
        observable_label = self._observable_label(measurement)
        metadata: dict[str, object] = {
            "pennylane_terminal_kind": terminal_kind,
            "pennylane_measurement_wires": target_wires,
        }
        if observable_label is not None:
            metadata["pennylane_observable_label"] = observable_label

        return SemanticOperationIR(
            kind=OperationKind.GATE,
            name=_TERMINAL_LABEL_BY_KIND[terminal_kind],
            target_wires=target_wires,
            hover_details=self._terminal_measurement_hover_details(
                terminal_kind,
                observable_label=observable_label,
                target_native_wires=target_native_wires,
                tape_wires=tape_wires,
                wire_labels=wire_labels,
            ),
            provenance=semantic_provenance(
                framework=self.framework_name,
                native_name=measurement.__class__.__name__,
                native_kind=terminal_kind,
                location=location,
            ),
            metadata=metadata,
        )

    def _terminal_measurement_kind(self, measurement: object) -> str | None:
        class_name = measurement.__class__.__name__.lower()
        if "density" in class_name:
            return "density_matrix"
        if "expect" in class_name:
            return "expval"
        if "variance" in class_name or class_name.startswith("var"):
            return "var"
        if "prob" in class_name:
            return "probs"
        if "sample" in class_name:
            return "sample"
        if "counts" in class_name:
            return "counts"
        if "state" in class_name:
            return "state"

        measurement_repr = repr(measurement).lower()
        if measurement_repr.startswith("expval("):
            return "expval"
        if measurement_repr.startswith("var("):
            return "var"
        if measurement_repr.startswith("probs("):
            return "probs"
        if measurement_repr.startswith("sample("):
            return "sample"
        if measurement_repr.startswith("countsmp("):
            return "counts"
        if measurement_repr.startswith("state("):
            return "state"
        if hasattr(measurement, "wires") and self._measurement_observable(measurement) is None:
            return "sample"
        return None

    def _terminal_measurement_targets(
        self,
        measurement: _PennyLaneMeasurementLike,
        *,
        tape_wires: Sequence[object],
    ) -> tuple[object, ...]:
        terminal_kind = self._terminal_measurement_kind(measurement)
        assert terminal_kind is not None
        if terminal_kind == "state":
            return tuple(tape_wires)

        measurement_wires = tuple(getattr(measurement, "wires", ()) or ())
        observable = self._measurement_observable(measurement)
        observable_wires = tuple(getattr(observable, "wires", ()) or ())
        if terminal_kind in {"expval", "var"}:
            return observable_wires or measurement_wires or tuple(tape_wires)
        return measurement_wires or tuple(tape_wires)

    def _measurement_observable(self, measurement: object) -> object | None:
        observable = getattr(measurement, "obs", None)
        if observable is not None:
            return observable
        return getattr(measurement, "observable", None)

    def _observable_label(self, measurement: object) -> str | None:
        observable = self._measurement_observable(measurement)
        if observable is None:
            return None
        return self._summarize_observable(observable)

    def _summarize_observable(self, observable: object) -> str:
        operand_labels = self._tensor_operand_labels(observable)
        if operand_labels is not None:
            joined = " @ ".join(operand_labels)
            if joined and len(joined) <= _OBSERVABLE_SUMMARY_LIMIT:
                return joined
            return "composite observable"

        raw_name = getattr(observable, "name", None)
        normalized_name = self._normalized_observable_name(raw_name)
        if normalized_name is not None and len(normalized_name) <= _OBSERVABLE_SUMMARY_LIMIT:
            return normalized_name
        return "composite observable"

    def _tensor_operand_labels(self, observable: object) -> tuple[str, ...] | None:
        operands = tuple(getattr(observable, "operands", ()) or ())
        if not operands:
            return None
        raw_name = self._normalized_observable_name(getattr(observable, "name", None))
        class_name = observable.__class__.__name__.lower()
        if raw_name is not None and raw_name.lower() not in _TENSOR_OBSERVABLE_NAMES:
            if class_name not in _TENSOR_OBSERVABLE_NAMES:
                return None
        operand_labels = tuple(self._summarize_observable(operand) for operand in operands)
        if any(label == "composite observable" for label in operand_labels):
            return ()
        return operand_labels

    def _normalized_observable_name(self, value: object) -> str | None:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        if isinstance(value, Sequence) and not isinstance(value, str):
            first_name = next(
                (str(item).strip() for item in value if str(item).strip()),
                "",
            )
            return first_name or None
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    def _terminal_measurement_hover_details(
        self,
        terminal_kind: str,
        *,
        observable_label: str | None,
        target_native_wires: Sequence[object],
        tape_wires: Sequence[object],
        wire_labels: Mapping[object, str],
    ) -> tuple[str, ...]:
        scope_detail = (
            "all wires"
            if tuple(target_native_wires) == tuple(tape_wires)
            else "selected wires: "
            + ", ".join(wire_labels.get(wire, str(wire)) for wire in target_native_wires)
        )
        return normalized_detail_lines(
            f"terminal output: {terminal_kind}",
            None if observable_label is None else f"observable: {observable_label}",
            scope_detail,
        )

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


def _safe_wrapped_tape_candidates(circuit: object) -> tuple[object, ...]:
    candidates: list[object] = []
    for attribute in ("_tape", "qtape", "tape"):
        candidate = _safe_materialized_attribute(circuit, attribute)
        if candidate is _MISSING_ATTRIBUTE:
            continue
        candidates.append(candidate)
    return tuple(candidates)


_MISSING_ATTRIBUTE = object()


def _safe_materialized_attribute(circuit: object, attribute: str) -> object:
    try:
        candidate = getattr_static(circuit, attribute)
    except AttributeError:
        return _MISSING_ATTRIBUTE
    if isinstance(candidate, property):
        return _MISSING_ATTRIBUTE
    return candidate
