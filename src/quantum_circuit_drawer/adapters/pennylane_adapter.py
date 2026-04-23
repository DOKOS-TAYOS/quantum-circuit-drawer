"""PennyLane adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from inspect import getattr_static
from typing import Protocol, SupportsFloat, cast

from ..exceptions import UnsupportedFrameworkError, UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.operations import CanonicalGateFamily, OperationKind
from ..ir.semantic import SemanticCircuitIR, SemanticOperationIR, pack_semantic_operations
from ..ir.wires import WireIR, WireKind
from ..utils.matrix_support import square_matrix
from ._fundamental_decompositions import expand_fundamental_semantic_gate
from ._helpers import (
    append_semantic_classical_conditions,
    build_classical_register,
    canonical_gate_spec,
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
_LINEAR_COMBINATION_OBSERVABLE_NAMES = frozenset({"sum", "hamiltonian", "linearcombination"})
_SCALED_OBSERVABLE_NAMES = frozenset({"sprod"})
_OBSERVABLE_SUMMARY_LIMIT = 24


@dataclass(frozen=True)
class _ObservableSummary:
    label: str
    native_type: str
    component_count: int | None = None
    component_label: str | None = None
    truncated: bool = False
    structure: str = "simple"


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
        for operation_index, operation in enumerate(tape.operations):
            semantic_operations.extend(
                self._convert_operation(
                    operation,
                    wire_ids,
                    mid_measure_targets=mid_measure_targets,
                    composite_mode=composite_mode,
                    explicit_matrices=explicit_matrices,
                    location=(operation_index,),
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
        location: tuple[int, ...] = (),
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
                        decomposition_origin=decomposition_origin,
                        location=location,
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
                location=location,
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
        if composite_mode == "expand":
            expanded_fundamental = expand_fundamental_semantic_gate(
                framework=self.framework_name,
                canonical_family=canonical_gate.family,
                raw_name=str(getattr(operation, "name", operation.__class__.__name__)),
                target_wires=tuple(wire_ids[wire] for wire in operation.wires),
                parameters=tuple(getattr(operation, "parameters", ()) or ()),
                location=location,
            )
            if expanded_fundamental:
                return list(expanded_fundamental)
        if composite_mode == "expand" and canonical_gate.family is CanonicalGateFamily.CUSTOM:
            decomposition = self._decomposition(operation)
            if decomposition:
                expanded_operations: list[SemanticOperationIR] = []
                composite_name = getattr(operation, "name", operation.__class__.__name__)
                for nested_index, nested_operation in enumerate(decomposition):
                    expanded_operations.extend(
                        self._convert_operation(
                            cast(_PennyLaneOperationLike, nested_operation),
                            wire_ids,
                            mid_measure_targets=mid_measure_targets,
                            composite_mode=composite_mode,
                            explicit_matrices=explicit_matrices,
                            decomposition_origin=composite_name,
                            location=(*location, nested_index),
                        )
                    )
                return expanded_operations

        native_name = getattr(operation, "name", operation.__class__.__name__)
        composite_label = (
            native_name
            if canonical_gate.family is CanonicalGateFamily.CUSTOM and decomposition_origin is None
            else None
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
                        native_name=native_name,
                        native_kind="swap",
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
                        location=location,
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
                        native_name=native_name,
                        native_kind="barrier",
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
                        location=location,
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
                    control_values=self._control_values_for_operation(operation),
                    parameters=parameters,
                    hover_details=normalized_detail_lines(
                        f"decomposed from: {decomposition_origin}"
                        if decomposition_origin is not None
                        else None
                    ),
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=native_name,
                        native_kind="controlled_gate",
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
                        location=location,
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
                    native_name=native_name,
                    native_kind=("composite" if composite_label is not None else "gate"),
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                    location=location,
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
        observable_summary = self._measurement_observable_summary(measurement)
        metadata: dict[str, object] = {
            "pennylane_terminal_kind": terminal_kind,
            "pennylane_measurement_wires": target_wires,
        }
        if observable_summary is not None:
            metadata["pennylane_observable_label"] = observable_summary.label

        return SemanticOperationIR(
            kind=OperationKind.GATE,
            name=_TERMINAL_LABEL_BY_KIND[terminal_kind],
            target_wires=target_wires,
            hover_details=self._terminal_measurement_hover_details(
                measurement=measurement,
                terminal_kind=terminal_kind,
                observable_summary=observable_summary,
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

    def _measurement_observable_summary(self, measurement: object) -> _ObservableSummary | None:
        observable = self._measurement_observable(measurement)
        if observable is None:
            return None
        return self._summarize_observable(observable)

    def _summarize_observable(self, observable: object) -> _ObservableSummary:
        scaled_summary = self._scaled_observable_summary(observable)
        if scaled_summary is not None:
            return scaled_summary

        linear_combination_summary = self._linear_combination_summary(observable)
        if linear_combination_summary is not None:
            return linear_combination_summary

        product_summary = self._product_observable_summary(observable)
        if product_summary is not None:
            return product_summary

        return self._simple_observable_summary(observable)

    def _product_observable_summary(self, observable: object) -> _ObservableSummary | None:
        if not self._observable_matches(observable, _TENSOR_OBSERVABLE_NAMES):
            return None
        operands = self._flatten_product_operands(observable)
        if not operands:
            return None
        operand_summaries = tuple(self._summarize_observable(operand) for operand in operands)
        return self._joined_observable_summary(
            native_type=self._observable_native_type(observable),
            components=operand_summaries,
            separator=" @ ",
            truncated_suffix=" @ ...",
            component_label="operands",
            structural_suffix="ops",
            structure="product",
        )

    def _scaled_observable_summary(self, observable: object) -> _ObservableSummary | None:
        if not self._observable_matches(observable, _SCALED_OBSERVABLE_NAMES):
            return None

        scalar = getattr(observable, "scalar", None)
        base = getattr(observable, "base", None)
        if base is None:
            terms = self._observable_terms(observable)
            if terms is None or len(terms) != 1:
                return None
            scalar, base = terms[0]

        base_summary = self._summarize_observable(base)
        base_label = self._parenthesized_observable_label(base_summary)
        full_label = f"{self._format_observable_scalar(scalar)} * {base_label}"
        if len(full_label) <= _OBSERVABLE_SUMMARY_LIMIT:
            return _ObservableSummary(
                label=full_label,
                native_type=self._observable_native_type(observable),
                component_count=1,
                component_label="terms",
                truncated=base_summary.truncated,
                structure="scaled",
            )

        truncated_label = f"{self._format_observable_scalar(scalar)} * ..."
        if len(truncated_label) <= _OBSERVABLE_SUMMARY_LIMIT:
            return _ObservableSummary(
                label=truncated_label,
                native_type=self._observable_native_type(observable),
                component_count=1,
                component_label="terms",
                truncated=True,
                structure="scaled",
            )

        return _ObservableSummary(
            label=self._structural_observable_fallback(
                native_type=self._observable_native_type(observable),
                component_count=1,
                component_label="term",
            ),
            native_type=self._observable_native_type(observable),
            component_count=1,
            component_label="terms",
            truncated=True,
            structure="scaled",
        )

    def _linear_combination_summary(self, observable: object) -> _ObservableSummary | None:
        if not self._observable_matches(observable, _LINEAR_COMBINATION_OBSERVABLE_NAMES):
            return None

        terms = self._observable_terms(observable)
        if terms is None:
            return None

        show_unity_coefficients = self._observable_native_type(observable).lower() in {
            "linearcombination",
            "hamiltonian",
        }
        term_summaries = tuple(
            self._linear_combination_term_label(
                coefficient=coefficient,
                operand=operand,
                show_unity_coefficient=show_unity_coefficients,
            )
            for coefficient, operand in terms
        )
        return self._joined_observable_summary(
            native_type=self._observable_native_type(observable),
            components=term_summaries,
            separator=" + ",
            truncated_suffix=" + ...",
            component_label="terms",
            structural_suffix="terms",
            structure="sum",
        )

    def _joined_observable_summary(
        self,
        *,
        native_type: str,
        components: Sequence[_ObservableSummary],
        separator: str,
        truncated_suffix: str,
        component_label: str,
        structural_suffix: str,
        structure: str,
    ) -> _ObservableSummary:
        labels = tuple(component.label for component in components)
        any_truncated = any(component.truncated for component in components)
        joined = separator.join(labels)
        if joined and len(joined) <= _OBSERVABLE_SUMMARY_LIMIT:
            return _ObservableSummary(
                label=joined,
                native_type=native_type,
                component_count=len(components),
                component_label=component_label,
                truncated=any_truncated,
                structure=structure,
            )

        truncated_label = self._truncate_joined_observable_label(
            labels,
            separator=separator,
            truncated_suffix=truncated_suffix,
        )
        if truncated_label is not None:
            return _ObservableSummary(
                label=truncated_label,
                native_type=native_type,
                component_count=len(components),
                component_label=component_label,
                truncated=True,
                structure=structure,
            )

        return _ObservableSummary(
            label=self._structural_observable_fallback(
                native_type=native_type,
                component_count=len(components),
                component_label=structural_suffix,
            ),
            native_type=native_type,
            component_count=len(components),
            component_label=component_label,
            truncated=True,
            structure=structure,
        )

    def _linear_combination_term_label(
        self,
        *,
        coefficient: object,
        operand: object,
        show_unity_coefficient: bool,
    ) -> _ObservableSummary:
        operand_summary = self._summarize_observable(operand)
        coefficient_text = self._format_observable_scalar(coefficient)
        if not show_unity_coefficient and coefficient_text == "1":
            return operand_summary
        return _ObservableSummary(
            label=f"{coefficient_text} * {self._parenthesized_observable_label(operand_summary)}",
            native_type=operand_summary.native_type,
            truncated=operand_summary.truncated,
            structure="scaled",
        )

    def _truncate_joined_observable_label(
        self,
        labels: Sequence[str],
        *,
        separator: str,
        truncated_suffix: str,
    ) -> str | None:
        prefix = ""
        for label in labels:
            candidate = label if not prefix else f"{prefix}{separator}{label}"
            if len(f"{candidate}{truncated_suffix}") <= _OBSERVABLE_SUMMARY_LIMIT:
                prefix = candidate
                continue
            break
        if not prefix:
            return None
        return f"{prefix}{truncated_suffix}"

    def _flatten_product_operands(self, observable: object) -> tuple[object, ...]:
        operands = tuple(getattr(observable, "operands", ()) or ())
        flattened: list[object] = []
        for operand in operands:
            if self._observable_matches(operand, _TENSOR_OBSERVABLE_NAMES):
                nested_operands = self._flatten_product_operands(operand)
                if nested_operands:
                    flattened.extend(nested_operands)
                    continue
            flattened.append(operand)
        return tuple(flattened)

    def _simple_observable_summary(self, observable: object) -> _ObservableSummary:
        native_type = self._observable_native_type(observable)
        if len(native_type) <= _OBSERVABLE_SUMMARY_LIMIT:
            return _ObservableSummary(label=native_type, native_type=native_type)

        class_name = observable.__class__.__name__.strip()
        if class_name and len(class_name) <= _OBSERVABLE_SUMMARY_LIMIT:
            return _ObservableSummary(label=class_name, native_type=class_name)

        return _ObservableSummary(
            label=self._deterministic_observable_fallback(
                native_type=native_type,
                class_name=class_name,
            ),
            native_type=native_type,
        )

    def _observable_terms(self, observable: object) -> tuple[tuple[object, object], ...] | None:
        terms = getattr(observable, "terms", None)
        if callable(terms):
            coefficients, operands = terms()
            coefficient_values = tuple(coefficients or ())
            operand_values = tuple(operands or ())
            if len(coefficient_values) == len(operand_values) and operand_values:
                return tuple(zip(coefficient_values, operand_values, strict=False))

        operands = tuple(getattr(observable, "operands", ()) or ())
        if not operands:
            return None
        coefficients = tuple(getattr(observable, "coeffs", ()) or ())
        if coefficients and len(coefficients) == len(operands):
            return tuple(zip(coefficients, operands, strict=False))
        if self._observable_matches(observable, {"sum"}):
            return tuple((1.0, operand) for operand in operands)
        return None

    def _observable_matches(self, observable: object, names: frozenset[str] | set[str]) -> bool:
        type_names = {
            name.lower()
            for name in (
                self._normalized_observable_name(getattr(observable, "name", None)),
                observable.__class__.__name__,
            )
            if name
        }
        return bool(type_names & set(names))

    def _observable_native_type(self, observable: object) -> str:
        raw_name = self._normalized_observable_name(getattr(observable, "name", None))
        if raw_name is not None:
            return raw_name
        class_name = observable.__class__.__name__.strip()
        if class_name:
            return class_name
        return "Observable"

    def _parenthesized_observable_label(self, summary: _ObservableSummary) -> str:
        if summary.structure == "simple":
            return summary.label
        return f"({summary.label})"

    def _structural_observable_fallback(
        self,
        *,
        native_type: str,
        component_count: int,
        component_label: str,
    ) -> str:
        structural_label = f"{native_type}[{component_count} {component_label}]"
        if len(structural_label) <= _OBSERVABLE_SUMMARY_LIMIT:
            return structural_label
        return self._deterministic_observable_fallback(
            native_type=native_type,
            class_name=native_type,
        )

    def _deterministic_observable_fallback(self, *, native_type: str, class_name: str) -> str:
        for candidate in (class_name, native_type):
            fallback = self._class_name_fallback(candidate)
            if fallback is not None:
                return fallback
        return "composite observable"

    def _class_name_fallback(self, class_name: str) -> str | None:
        normalized_class_name = class_name.strip()
        if not normalized_class_name:
            return None
        full_fallback = f"{normalized_class_name}[...]"
        if len(full_fallback) <= _OBSERVABLE_SUMMARY_LIMIT:
            return full_fallback
        max_prefix_length = _OBSERVABLE_SUMMARY_LIMIT - len("[...]")
        if max_prefix_length <= 0:
            return None
        return f"{normalized_class_name[:max_prefix_length]}[...]"

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
        measurement: _PennyLaneMeasurementLike,
        terminal_kind: str,
        *,
        observable_summary: _ObservableSummary | None,
        target_native_wires: Sequence[object],
        tape_wires: Sequence[object],
        wire_labels: Mapping[object, str],
    ) -> tuple[str, ...]:
        scope_detail = self._terminal_measurement_scope_detail(
            measurement,
            terminal_kind=terminal_kind,
            target_native_wires=target_native_wires,
            tape_wires=tape_wires,
            wire_labels=wire_labels,
        )
        return normalized_detail_lines(
            f"terminal output: {terminal_kind}",
            None if observable_summary is None else f"observable: {observable_summary.label}",
            None
            if observable_summary is None
            else f"observable type: {observable_summary.native_type}",
            (
                None
                if observable_summary is None
                or observable_summary.component_count is None
                or observable_summary.component_label is None
                else f"observable {observable_summary.component_label}: "
                f"{observable_summary.component_count}"
            ),
            None
            if observable_summary is None or not observable_summary.truncated
            else "observable summary: truncated",
            scope_detail,
        )

    def _terminal_measurement_scope_detail(
        self,
        measurement: _PennyLaneMeasurementLike,
        *,
        terminal_kind: str,
        target_native_wires: Sequence[object],
        tape_wires: Sequence[object],
        wire_labels: Mapping[object, str],
    ) -> str:
        if terminal_kind == "state":
            return "all wires"

        measurement_wires = tuple(getattr(measurement, "wires", ()) or ())
        if terminal_kind in {"expval", "var"}:
            if (
                tuple(target_native_wires) == tuple(tape_wires)
                and len(tuple(target_native_wires)) > 1
            ):
                return "all wires"
            return "selected wires: " + ", ".join(
                wire_labels.get(wire, str(wire)) for wire in target_native_wires
            )

        if measurement_wires:
            return "selected wires: " + ", ".join(
                wire_labels.get(wire, str(wire)) for wire in measurement_wires
            )
        return "all wires"

    def _format_observable_scalar(self, value: object) -> str:
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, int | float):
            return f"{value:g}"
        try:
            return f"{float(self._coercible_observable_scalar(value)):g}"
        except (OverflowError, TypeError, ValueError):
            normalized_value = self._normalized_observable_name(value)
            if normalized_value is not None:
                return normalized_value
            return str(value)

    def _coercible_observable_scalar(self, value: object) -> str | SupportsFloat:
        if isinstance(value, str):
            return value
        if hasattr(value, "__float__"):
            return cast("SupportsFloat", value)
        raise TypeError("unsupported observable scalar")

    def _control_values_for_operation(
        self,
        operation: object,
    ) -> tuple[tuple[int, ...], ...]:
        raw_values = getattr(operation, "control_values", ())
        if raw_values is None:
            return ()

        normalized_entries: list[tuple[int, ...]] = []
        for raw_entry in tuple(raw_values):
            if isinstance(raw_entry, Sequence) and not isinstance(raw_entry, str | bytes):
                values = tuple(int(value) for value in raw_entry)
            else:
                values = (int(raw_entry),)
            normalized_entries.append(values)
        if all(entry == (1,) for entry in normalized_entries):
            return ()
        return tuple(normalized_entries)

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
