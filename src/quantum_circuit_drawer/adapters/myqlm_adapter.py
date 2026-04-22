"""MyQLM adapter."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Protocol, cast

from ..config import UnsupportedPolicy
from ..diagnostics import DiagnosticSeverity, RenderDiagnostic
from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.operations import OperationKind
from ..ir.semantic import SemanticCircuitIR, SemanticOperationIR, pack_semantic_operations
from ..ir.wires import WireIR, WireKind
from ._helpers import (
    CanonicalGateSpec,
    append_semantic_classical_conditions,
    build_classical_register,
    canonical_gate_spec,
    extract_dependency_types,
    normalized_detail_lines,
    resolve_composite_mode,
    semantic_provenance,
    sequential_bit_labels,
)
from .base import BaseAdapter

_DEFAULT_OPERATION_TYPE_BY_INT: dict[int, str] = {
    0: "GATETYPE",
    1: "MEASURE",
    2: "RESET",
    3: "CLASSIC",
    4: "CLASSICCTRL",
    5: "BREAK",
    6: "REMAP",
}


def _build_operation_type_map() -> dict[int, str]:
    mapping = dict(_DEFAULT_OPERATION_TYPE_BY_INT)
    try:
        from qat.comm.datamodel.ttypes import OpType
    except (ImportError, ModuleNotFoundError):
        return mapping

    for name in ("GATETYPE", "MEASURE", "RESET", "CLASSIC", "CLASSICCTRL", "BREAK", "REMAP"):
        value = getattr(OpType, name, None)
        if isinstance(value, int):
            mapping[int(value)] = name
    return mapping


_OPERATION_TYPE_BY_INT = _build_operation_type_map()
_CLASSICAL_BIT_REFERENCE_PATTERN = re.compile(r"c\[(\d+)\]")


def _unsupported_policy_from_options(options: Mapping[str, object] | None) -> UnsupportedPolicy:
    if options is None:
        return UnsupportedPolicy.RAISE
    raw_policy = options.get("unsupported_policy", UnsupportedPolicy.RAISE)
    if isinstance(raw_policy, UnsupportedPolicy):
        return raw_policy
    try:
        return UnsupportedPolicy(str(raw_policy))
    except ValueError:
        return UnsupportedPolicy.RAISE


class _MyQLMSyntaxLike(Protocol):
    name: str
    parameters: Sequence[object]


class _MyQLMOpLike(Protocol):
    gate: str | None
    qbits: Sequence[int]
    type: object
    cbits: Sequence[int] | None
    formula: str | None
    remap: Sequence[int] | None


class _MyQLMCircuitImplementationLike(Protocol):
    ops: Sequence[_MyQLMOpLike]
    ancillas: int
    nbqbits: int


class _MyQLMGateDefinitionLike(Protocol):
    name: str
    arity: int
    syntax: _MyQLMSyntaxLike | None
    nbctrls: int | None
    subgate: str | None
    circuit_implementation: _MyQLMCircuitImplementationLike | None


class _MyQLMCircuitLike(Protocol):
    ops: Sequence[_MyQLMOpLike]
    gateDic: Mapping[str, _MyQLMGateDefinitionLike]
    nbqbits: int
    nbcbits: int
    name: str | None


class MyQLMAdapter(BaseAdapter):
    """Convert ``qat.core.Circuit`` objects into semantic IR and ``CircuitIR``."""

    framework_name = "myqlm"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        circuit_types = extract_dependency_types("qat", ("core.Circuit",))
        return bool(circuit_types) and isinstance(circuit, circuit_types)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        semantic_ir = self.to_semantic_ir(circuit, options=options)
        assert semantic_ir is not None
        return lower_semantic_circuit(semantic_ir)

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("MyQLMAdapter received a non-MyQLM circuit")

        typed_circuit = cast(_MyQLMCircuitLike, circuit)
        composite_mode = resolve_composite_mode(options)
        quantum_count = max(
            self._declared_quantum_count(typed_circuit), self._used_qubit_count(circuit)
        )
        classical_count = max(
            self._declared_classical_count(typed_circuit),
            self._used_classical_count(circuit),
        )
        qubit_wire_ids = {index: f"q{index}" for index in range(quantum_count)}
        quantum_wires = [
            WireIR(
                id=qubit_wire_ids[index],
                index=index,
                kind=WireKind.QUANTUM,
                label=f"q{index}",
            )
            for index in range(quantum_count)
        ]
        classical_wires, classical_bit_targets = build_classical_register(
            sequential_bit_labels(classical_count)
        )
        classical_targets = {index: target for index, target in enumerate(classical_bit_targets)}
        unsupported_policy = _unsupported_policy_from_options(options)
        diagnostics: list[RenderDiagnostic] = []
        semantic_operations: list[SemanticOperationIR] = []

        for operation_index, operation in enumerate(typed_circuit.ops):
            semantic_operations.extend(
                self._convert_operation(
                    operation,
                    gate_definitions=typed_circuit.gateDic,
                    qubit_wire_ids=qubit_wire_ids,
                    classical_targets=classical_targets,
                    composite_mode=composite_mode,
                    unsupported_policy=unsupported_policy,
                    diagnostics=diagnostics,
                    location=(operation_index,),
                    decomposition_origin=None,
                    composite_label=None,
                )
            )

        return SemanticCircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=pack_semantic_operations(semantic_operations),
            name=typed_circuit.name,
            metadata={
                "framework": self.framework_name,
                "diagnostics": tuple(diagnostics),
            },
            diagnostics=tuple(diagnostics),
        )

    def _declared_quantum_count(self, circuit: _MyQLMCircuitLike) -> int:
        return max(int(circuit.nbqbits), 0)

    def _declared_classical_count(self, circuit: _MyQLMCircuitLike) -> int:
        return max(int(circuit.nbcbits), 0)

    def _used_qubit_count(self, circuit: object) -> int:
        operations = tuple(getattr(circuit, "ops", ()) or ())
        max_index = max(
            (max(getattr(operation, "qbits", ()) or (), default=-1) for operation in operations),
            default=-1,
        )
        return max_index + 1

    def _used_classical_count(self, circuit: object) -> int:
        operations = tuple(getattr(circuit, "ops", ()) or ())
        max_index = max(
            (max(getattr(operation, "cbits", ()) or (), default=-1) for operation in operations),
            default=-1,
        )
        return max_index + 1

    def _convert_operation(
        self,
        operation: _MyQLMOpLike,
        *,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        qubit_wire_ids: Mapping[int, str],
        classical_targets: Mapping[int, tuple[str, str]],
        composite_mode: str,
        unsupported_policy: UnsupportedPolicy,
        diagnostics: list[RenderDiagnostic],
        location: tuple[int, ...],
        decomposition_origin: str | None,
        composite_label: str | None,
    ) -> list[SemanticOperationIR]:
        operation_type = self._operation_type_name(operation.type)
        try:
            if operation_type == "GATETYPE":
                return self._convert_gate_application(
                    operation,
                    gate_definitions=gate_definitions,
                    qubit_wire_ids=qubit_wire_ids,
                    classical_targets=classical_targets,
                    composite_mode=composite_mode,
                    unsupported_policy=unsupported_policy,
                    diagnostics=diagnostics,
                    location=location,
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                )
            if operation_type == "CLASSICCTRL":
                converted = self._convert_gate_application(
                    operation,
                    gate_definitions=gate_definitions,
                    qubit_wire_ids=qubit_wire_ids,
                    classical_targets=classical_targets,
                    composite_mode=composite_mode,
                    unsupported_policy=unsupported_policy,
                    diagnostics=diagnostics,
                    location=location,
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                )
                condition = self._classical_condition_for_operation(operation, classical_targets)
                return [
                    replace(
                        append_semantic_classical_conditions(node, (condition,)),
                        hover_details=(
                            *node.hover_details,
                            f"classical control: {condition.expression}",
                        ),
                        provenance=semantic_provenance(
                            framework=self.framework_name,
                            native_name=node.provenance.native_name or node.name,
                            native_kind="classicctrl",
                            decomposition_origin=node.provenance.decomposition_origin,
                            composite_label=node.provenance.composite_label,
                            location=node.provenance.location,
                        ),
                    )
                    for node in converted
                ]
            if operation_type == "MEASURE":
                return self._convert_measurement(
                    operation,
                    qubit_wire_ids,
                    classical_targets,
                    location=location,
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                )
            if operation_type == "RESET":
                return self._convert_reset(
                    operation,
                    qubit_wire_ids,
                    classical_targets=classical_targets,
                    location=location,
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                )
            if operation_type == "REMAP":
                return self._convert_remap(
                    operation,
                    qubit_wire_ids,
                    location=location,
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                )
            if operation_type in {"BREAK", "CLASSIC"}:
                return self._convert_classical_box(
                    operation,
                    operation_type=operation_type,
                    classical_targets=classical_targets,
                    location=location,
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                )
            raise UnsupportedOperationError(
                f"unsupported myQLM operation type '{operation_type.lower()}'"
            )
        except UnsupportedOperationError as exc:
            placeholder = self._recover_as_placeholder(
                operation,
                operation_type=operation_type,
                error=exc,
                gate_definitions=gate_definitions,
                qubit_wire_ids=qubit_wire_ids,
                unsupported_policy=unsupported_policy,
                diagnostics=diagnostics,
                location=location,
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
            if placeholder is not None:
                return placeholder
            raise

    def _convert_gate_application(
        self,
        operation: _MyQLMOpLike,
        *,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        qubit_wire_ids: Mapping[int, str],
        classical_targets: Mapping[int, tuple[str, str]],
        composite_mode: str,
        unsupported_policy: UnsupportedPolicy,
        diagnostics: list[RenderDiagnostic],
        location: tuple[int, ...],
        decomposition_origin: str | None,
        composite_label: str | None,
    ) -> list[SemanticOperationIR]:
        gate_key = operation.gate
        if gate_key is None:
            raise UnsupportedOperationError("myQLM gate operation is missing a gate definition")

        target_wires = self._target_wire_ids(operation.qbits, qubit_wire_ids)
        definition = gate_definitions.get(gate_key)
        display_name = self._gate_display_name(definition, gate_key)
        parameters = self._gate_parameters(definition)

        if definition is not None and definition.circuit_implementation is not None:
            implementation = definition.circuit_implementation
            ancilla_count = int(getattr(implementation, "ancillas", 0) or 0)
            if composite_mode == "expand" and ancilla_count == 0:
                return self._expand_circuit_implementation(
                    implementation,
                    gate_definitions=gate_definitions,
                    qubit_wire_ids=target_wires,
                    classical_targets=classical_targets,
                    composite_mode=composite_mode,
                    unsupported_policy=unsupported_policy,
                    diagnostics=diagnostics,
                    location=location,
                    decomposition_origin=display_name,
                    composite_label=display_name,
                )
            if composite_mode == "expand" and ancilla_count > 0:
                diagnostics.append(
                    RenderDiagnostic(
                        code="myqlm_composite_ancilla_compact_render",
                        message=(
                            f"Rendered myQLM composite {display_name!r} as a compact box because "
                            "its implementation uses ancillas."
                        ),
                        severity=DiagnosticSeverity.INFO,
                    )
                )
            return [
                self._compact_composite_operation(
                    display_name=display_name,
                    target_wires=tuple(target_wires.values()),
                    parameters=parameters,
                    location=location,
                    ancilla_count=ancilla_count,
                    effective_arity=int(getattr(implementation, "nbqbits", len(target_wires)) or 0)
                    or len(target_wires),
                )
            ]

        control_count = self._control_count(definition)
        if control_count > 0:
            ordered_wires = tuple(target_wires.values())
            if len(ordered_wires) <= control_count:
                raise UnsupportedOperationError(
                    f"myQLM controlled gate '{display_name}' has no target wires after controls"
                )
            base_gate_spec = self._subgate_spec(definition, gate_definitions)
            return [
                SemanticOperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=base_gate_spec.label,
                    canonical_family=base_gate_spec.family,
                    target_wires=ordered_wires[control_count:],
                    control_wires=ordered_wires[:control_count],
                    parameters=parameters,
                    hover_details=normalized_detail_lines(
                        f"native: {display_name}",
                        (
                            f"decomposed from: {decomposition_origin}"
                            if decomposition_origin is not None
                            else None
                        ),
                    ),
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=display_name,
                        native_kind="controlled_gate",
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
                        location=location,
                    ),
                )
            ]

        canonical_gate = canonical_gate_spec(display_name)
        ordered_wires = tuple(target_wires.values())
        if canonical_gate.label == "SWAP":
            return [
                SemanticOperationIR(
                    kind=OperationKind.SWAP,
                    name="SWAP",
                    target_wires=ordered_wires,
                    hover_details=normalized_detail_lines(
                        f"native: {display_name}",
                        (
                            f"decomposed from: {decomposition_origin}"
                            if decomposition_origin is not None
                            else None
                        ),
                    ),
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=display_name,
                        native_kind="swap",
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
                        location=location,
                    ),
                )
            ]
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=ordered_wires,
                parameters=parameters,
                hover_details=normalized_detail_lines(
                    f"native: {display_name}",
                    (
                        f"decomposed from: {decomposition_origin}"
                        if decomposition_origin is not None
                        else None
                    ),
                ),
                provenance=semantic_provenance(
                    framework=self.framework_name,
                    native_name=display_name,
                    native_kind="gate",
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                    location=location,
                ),
            )
        ]

    def _expand_circuit_implementation(
        self,
        implementation: _MyQLMCircuitImplementationLike,
        *,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        qubit_wire_ids: Mapping[int, str],
        classical_targets: Mapping[int, tuple[str, str]],
        composite_mode: str,
        unsupported_policy: UnsupportedPolicy,
        diagnostics: list[RenderDiagnostic],
        location: tuple[int, ...],
        decomposition_origin: str,
        composite_label: str,
    ) -> list[SemanticOperationIR]:
        ancilla_count = int(getattr(implementation, "ancillas", 0) or 0)
        required_qubits = int(getattr(implementation, "nbqbits", len(qubit_wire_ids)) or 0)
        if ancilla_count > 0:
            raise UnsupportedOperationError(
                "myQLM composite operations with ancillas must be rendered as compact boxes"
            )
        if required_qubits > len(qubit_wire_ids):
            raise UnsupportedOperationError(
                "myQLM composite operation requires more qubits than the enclosing call provides"
            )

        nested_wire_ids = {index: qubit_wire_ids[index] for index in range(required_qubits)}
        expanded: list[SemanticOperationIR] = []
        for nested_index, nested_operation in enumerate(implementation.ops):
            expanded.extend(
                self._convert_operation(
                    nested_operation,
                    gate_definitions=gate_definitions,
                    qubit_wire_ids=nested_wire_ids,
                    classical_targets=classical_targets,
                    composite_mode=composite_mode,
                    unsupported_policy=unsupported_policy,
                    diagnostics=diagnostics,
                    location=(*location, nested_index),
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                )
            )
        return expanded

    def _compact_composite_operation(
        self,
        *,
        display_name: str,
        target_wires: tuple[str, ...],
        parameters: tuple[object, ...],
        location: tuple[int, ...],
        ancilla_count: int = 0,
        effective_arity: int | None = None,
    ) -> SemanticOperationIR:
        hover_details: list[str] = [
            f"native: {display_name}",
            f"composite: {display_name}",
        ]
        if ancilla_count > 0:
            hover_details.append(f"ancillas: {ancilla_count}")
            if effective_arity is not None:
                hover_details.append(f"arity: {effective_arity}")
        return SemanticOperationIR(
            kind=OperationKind.GATE,
            name=display_name,
            label=display_name,
            target_wires=target_wires,
            parameters=parameters,
            annotations=(f"native: {display_name}",),
            hover_details=normalized_detail_lines(*hover_details),
            provenance=semantic_provenance(
                framework=self.framework_name,
                native_name=display_name,
                native_kind="composite",
                composite_label=display_name,
                location=location,
            ),
        )

    def _convert_measurement(
        self,
        operation: _MyQLMOpLike,
        qubit_wire_ids: Mapping[int, str],
        classical_targets: Mapping[int, tuple[str, str]],
        *,
        location: tuple[int, ...],
        decomposition_origin: str | None,
        composite_label: str | None,
    ) -> list[SemanticOperationIR]:
        qubits = tuple(operation.qbits)
        classical_bits = tuple(operation.cbits or ())
        if len(qubits) != len(classical_bits):
            raise UnsupportedOperationError("myQLM measurement expects matching qubit/cbit counts")

        converted_measurements: list[SemanticOperationIR] = []
        for pair_index, (qubit_index, cbit_index) in enumerate(
            zip(qubits, classical_bits, strict=True)
        ):
            classical_target, bit_label = self._classical_target(cbit_index, classical_targets)
            converted_measurements.append(
                SemanticOperationIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=(self._wire_id_for_index(qubit_index, qubit_wire_ids),),
                    classical_target=classical_target,
                    hover_details=normalized_detail_lines(
                        f"classical target: {bit_label}",
                        (
                            f"decomposed from: {decomposition_origin}"
                            if decomposition_origin is not None
                            else None
                        ),
                    ),
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name="MEASURE",
                        native_kind="measurement",
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
                        location=(*location, pair_index),
                    ),
                    metadata={"classical_bit_label": bit_label},
                )
            )
        return converted_measurements

    def _convert_reset(
        self,
        operation: _MyQLMOpLike,
        qubit_wire_ids: Mapping[int, str],
        *,
        classical_targets: Mapping[int, tuple[str, str]],
        location: tuple[int, ...],
        decomposition_origin: str | None,
        composite_label: str | None,
    ) -> list[SemanticOperationIR]:
        qubits = tuple(operation.qbits)
        formula_text = (operation.formula or "").strip()
        classical_bits = tuple(int(index) for index in (operation.cbits or ()))

        if not qubits:
            if formula_text or classical_bits:
                raise UnsupportedOperationError(
                    "myQLM classical-only reset operations are not supported yet"
                )
            raise UnsupportedOperationError("myQLM reset operation does not reference any qubits")

        classical_bit_labels = tuple(
            self._classical_target(classical_index, classical_targets)[1]
            for classical_index in classical_bits
        )
        hover_details = normalized_detail_lines(
            "native: RESET",
            (
                f"classical bits: {', '.join(classical_bit_labels)}"
                if classical_bit_labels
                else None
            ),
            (f"formula raw: {formula_text}" if formula_text else None),
            (
                f"decomposed from: {decomposition_origin}"
                if decomposition_origin is not None
                else None
            ),
        )
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name="RESET",
                target_wires=(self._wire_id_for_index(qubit_index, qubit_wire_ids),),
                hover_details=hover_details,
                provenance=semantic_provenance(
                    framework=self.framework_name,
                    native_name="RESET",
                    native_kind="reset",
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                    location=(*location, reset_index),
                ),
                metadata={
                    "classical_bits": classical_bit_labels,
                    "formula_raw": formula_text or None,
                },
            )
            for reset_index, qubit_index in enumerate(qubits)
        ]

    def _convert_remap(
        self,
        operation: _MyQLMOpLike,
        qubit_wire_ids: Mapping[int, str],
        *,
        location: tuple[int, ...],
        decomposition_origin: str | None,
        composite_label: str | None,
    ) -> list[SemanticOperationIR]:
        target_wires = tuple(self._target_wire_ids(operation.qbits, qubit_wire_ids).values())
        if not target_wires:
            raise UnsupportedOperationError("myQLM REMAP operation does not reference any qubits")
        hover_details = normalized_detail_lines(
            "native: REMAP",
            self._remap_summary(operation, qubit_wire_ids),
            (
                f"decomposed from: {decomposition_origin}"
                if decomposition_origin is not None
                else None
            ),
        )
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name="REMAP",
                label="REMAP",
                target_wires=target_wires,
                hover_details=hover_details,
                provenance=semantic_provenance(
                    framework=self.framework_name,
                    native_name="REMAP",
                    native_kind="remap",
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                    location=location,
                ),
            )
        ]

    def _convert_classical_box(
        self,
        operation: _MyQLMOpLike,
        *,
        operation_type: str,
        classical_targets: Mapping[int, tuple[str, str]],
        location: tuple[int, ...],
        decomposition_origin: str | None,
        composite_label: str | None,
    ) -> list[SemanticOperationIR]:
        classical_bits = tuple(int(index) for index in (operation.cbits or ()))
        if not classical_bits:
            raise UnsupportedOperationError(
                f"myQLM {operation_type.lower()} operation requires at least one classical bit"
            )

        resolved_targets = tuple(
            self._classical_target(classical_index, classical_targets)
            for classical_index in classical_bits
        )
        bit_labels = tuple(bit_label for _, bit_label in resolved_targets)
        target_wires = self._classical_box_target_wires(
            operation_type=operation_type,
            resolved_targets=resolved_targets,
        )
        condition = self._safe_classical_condition_for_operation(operation, classical_targets)
        formula_text = (operation.formula or "").strip()

        hover_details = normalized_detail_lines(
            f"native: {operation_type}",
            f"classical op: {operation_type.lower()}",
            (
                f"classical target: {bit_labels[0]}"
                if operation_type == "CLASSIC"
                else "effect: break when classical condition holds"
            ),
            f"cbits: {', '.join(bit_labels)}",
            (f"formula: {formula_text}" if formula_text and condition is not None else None),
            (f"formula raw: {formula_text}" if formula_text and condition is None else None),
            (f"condition: {condition.expression}" if condition is not None else None),
            (
                f"decomposed from: {decomposition_origin}"
                if decomposition_origin is not None
                else None
            ),
        )

        semantic_operation = SemanticOperationIR(
            kind=OperationKind.GATE,
            name=operation_type,
            label=operation_type,
            target_wires=target_wires,
            hover_details=hover_details,
            provenance=semantic_provenance(
                framework=self.framework_name,
                native_name=operation_type,
                native_kind=operation_type.lower(),
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
                location=location,
            ),
            metadata={
                "classical_bits": bit_labels,
                "classical_target_bit": bit_labels[0] if operation_type == "CLASSIC" else None,
            },
        )
        if condition is None:
            return [semantic_operation]
        return [append_semantic_classical_conditions(semantic_operation, (condition,))]

    def _classical_box_target_wires(
        self,
        *,
        operation_type: str,
        resolved_targets: Sequence[tuple[str, str]],
    ) -> tuple[str, ...]:
        if operation_type == "CLASSIC":
            return (resolved_targets[0][0],)
        return tuple(dict.fromkeys(wire_id for wire_id, _ in resolved_targets))

    def _remap_summary(
        self,
        operation: _MyQLMOpLike,
        qubit_wire_ids: Mapping[int, str],
    ) -> str:
        qubits = tuple(int(index) for index in operation.qbits)
        remap_values = tuple(int(index) for index in (operation.remap or ()))
        if remap_values and len(remap_values) == len(qubits):
            try:
                mappings = ", ".join(
                    f"{self._wire_id_for_index(source_index, qubit_wire_ids)}->"
                    f"{self._wire_id_for_index(target_index, qubit_wire_ids)}"
                    for source_index, target_index in zip(qubits, remap_values, strict=True)
                )
            except UnsupportedOperationError:
                pass
            else:
                return f"remap: {mappings}"
        return f"remap raw: qbits={qubits}, remap={remap_values}"

    def _classical_condition_for_operation(
        self,
        operation: _MyQLMOpLike,
        classical_targets: Mapping[int, tuple[str, str]],
    ) -> ClassicalConditionIR:
        classical_bits = tuple(operation.cbits or ())
        if not classical_bits:
            raise UnsupportedOperationError(
                "myQLM classical control requires at least one classical control bit"
            )

        resolved_targets = tuple(
            self._classical_target(classical_index, classical_targets)
            for classical_index in classical_bits
        )
        wire_ids = tuple(wire_id for wire_id, _ in resolved_targets)
        bit_labels = tuple(bit_label for _, bit_label in resolved_targets)

        expression_text = (operation.formula or "").strip()
        if not expression_text:
            if len(bit_labels) == 1:
                expression_text = f"{bit_labels[0]}=1"
            else:
                expression_text = " && ".join(f"{bit_label}=1" for bit_label in bit_labels)
        if not expression_text.startswith("if "):
            expression_text = f"if {expression_text}"

        return ClassicalConditionIR(
            wire_ids=wire_ids,
            expression=expression_text,
            metadata={"classical_bits": bit_labels},
        )

    def _safe_classical_condition_for_operation(
        self,
        operation: _MyQLMOpLike,
        classical_targets: Mapping[int, tuple[str, str]],
    ) -> ClassicalConditionIR | None:
        formula_text = (operation.formula or "").strip()
        if formula_text and not self._formula_references_known_bits(formula_text, operation.cbits):
            return None
        try:
            return self._classical_condition_for_operation(operation, classical_targets)
        except UnsupportedOperationError:
            return None

    def _formula_references_known_bits(
        self,
        formula_text: str,
        classical_bits: Sequence[int] | None,
    ) -> bool:
        known_bits = {int(index) for index in (classical_bits or ())}
        referenced_bits = {
            int(match.group(1)) for match in _CLASSICAL_BIT_REFERENCE_PATTERN.finditer(formula_text)
        }
        return referenced_bits.issubset(known_bits)

    def _recover_as_placeholder(
        self,
        operation: _MyQLMOpLike,
        *,
        operation_type: str,
        error: UnsupportedOperationError,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        qubit_wire_ids: Mapping[int, str],
        unsupported_policy: UnsupportedPolicy,
        diagnostics: list[RenderDiagnostic],
        location: tuple[int, ...],
        decomposition_origin: str | None,
        composite_label: str | None,
    ) -> list[SemanticOperationIR] | None:
        if unsupported_policy is not UnsupportedPolicy.PLACEHOLDER:
            return None
        if operation_type == "MEASURE":
            return None

        target_wires = self._placeholder_target_wires(operation, qubit_wire_ids)
        if not target_wires:
            return None

        display_name = self._placeholder_display_name(
            operation,
            operation_type=operation_type,
            gate_definitions=gate_definitions,
        )
        diagnostics.append(
            RenderDiagnostic(
                code="unsupported_operation_placeholder",
                message=(
                    f"Rendered unsupported myQLM operation {display_name!r} as a placeholder: "
                    f"{error}"
                ),
                severity=DiagnosticSeverity.WARNING,
            )
        )
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name=display_name,
                label=display_name,
                target_wires=(wire_id,),
                hover_details=normalized_detail_lines(
                    "unsupported placeholder",
                    f"reason: {error}",
                    (
                        f"decomposed from: {decomposition_origin}"
                        if decomposition_origin is not None
                        else None
                    ),
                ),
                provenance=semantic_provenance(
                    framework=self.framework_name,
                    native_name=display_name,
                    native_kind=operation_type.lower(),
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                    location=(*location, placeholder_index),
                ),
                metadata={"display_subtitle": "unsupported"},
            )
            for placeholder_index, wire_id in enumerate(target_wires)
        ]

    def _placeholder_target_wires(
        self,
        operation: _MyQLMOpLike,
        qubit_wire_ids: Mapping[int, str],
    ) -> tuple[str, ...]:
        qubit_indexes = tuple(operation.qbits)
        if not qubit_indexes:
            return ()
        return tuple(self._target_wire_ids(qubit_indexes, qubit_wire_ids).values())

    def _placeholder_display_name(
        self,
        operation: _MyQLMOpLike,
        *,
        operation_type: str,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
    ) -> str:
        if operation.gate is not None:
            return self._gate_display_name(gate_definitions.get(operation.gate), operation.gate)
        return operation_type

    def _operation_type_name(self, raw_type: object) -> str:
        if hasattr(raw_type, "name"):
            return str(getattr(raw_type, "name")).upper()
        if isinstance(raw_type, str):
            return raw_type.upper()
        if isinstance(raw_type, int):
            return _OPERATION_TYPE_BY_INT.get(raw_type, str(raw_type)).upper()
        return str(raw_type).upper()

    def _gate_display_name(
        self,
        definition: _MyQLMGateDefinitionLike | None,
        gate_key: str,
    ) -> str:
        if definition is not None and definition.syntax is not None and definition.syntax.name:
            return str(definition.syntax.name)
        if definition is not None and definition.name:
            return str(definition.name)
        return gate_key

    def _gate_parameters(
        self,
        definition: _MyQLMGateDefinitionLike | None,
    ) -> tuple[object, ...]:
        if definition is None or definition.syntax is None:
            return ()
        return tuple(
            self._normalize_parameter_value(parameter)
            for parameter in (definition.syntax.parameters or ())
        )

    def _normalize_parameter_value(self, parameter: object) -> object:
        if isinstance(parameter, bool | int | float | complex | str):
            return parameter

        int_value = getattr(parameter, "int_p", None)
        if int_value is not None:
            return int(int_value)

        double_value = getattr(parameter, "double_p", None)
        if double_value is not None:
            return float(double_value)

        string_value = getattr(parameter, "string_p", None)
        if isinstance(string_value, str) and string_value:
            return string_value

        complex_value = self._complex_parameter_value(getattr(parameter, "complex_p", None))
        if complex_value is not None:
            return complex_value

        return parameter

    def _complex_parameter_value(self, value: object) -> complex | None:
        if value is None:
            return None

        real_part = getattr(value, "re", getattr(value, "real", None))
        imaginary_part = getattr(value, "im", getattr(value, "imag", None))
        if isinstance(real_part, int | float) and isinstance(imaginary_part, int | float):
            return complex(float(real_part), float(imaginary_part))
        return None

    def _control_count(self, definition: _MyQLMGateDefinitionLike | None) -> int:
        if definition is None:
            return 0
        control_count = getattr(definition, "nbctrls", None)
        if control_count is None:
            return 0
        return int(control_count)

    def _subgate_spec(
        self,
        definition: _MyQLMGateDefinitionLike | None,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
    ) -> CanonicalGateSpec:
        if definition is None or definition.subgate is None:
            raise UnsupportedOperationError("myQLM controlled gate is missing its subgate")
        return self._resolve_gate_spec(str(definition.subgate), gate_definitions, seen=set())

    def _resolve_gate_spec(
        self,
        gate_key: str,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        *,
        seen: set[str],
    ) -> CanonicalGateSpec:
        if gate_key in seen:
            raise UnsupportedOperationError(
                f"myQLM gate definition cycle detected for '{gate_key}'"
            )
        seen.add(gate_key)
        definition = gate_definitions.get(gate_key)
        if definition is None:
            return canonical_gate_spec(gate_key)
        if definition.subgate is not None and self._control_count(definition) > 0:
            return self._resolve_gate_spec(str(definition.subgate), gate_definitions, seen=seen)
        return canonical_gate_spec(self._gate_display_name(definition, gate_key))

    def _target_wire_ids(
        self,
        qubit_indexes: Sequence[int],
        qubit_wire_ids: Mapping[int, str],
    ) -> dict[int, str]:
        return {
            position: self._wire_id_for_index(qubit_index, qubit_wire_ids)
            for position, qubit_index in enumerate(qubit_indexes)
        }

    def _wire_id_for_index(self, qubit_index: int, qubit_wire_ids: Mapping[int, str]) -> str:
        try:
            return qubit_wire_ids[int(qubit_index)]
        except KeyError as exc:
            raise UnsupportedOperationError(
                f"myQLM operation references unknown qubit index {qubit_index}"
            ) from exc

    def _classical_target(
        self,
        classical_index: int,
        classical_targets: Mapping[int, tuple[str, str]],
    ) -> tuple[str, str]:
        try:
            return classical_targets[int(classical_index)]
        except KeyError as exc:
            raise UnsupportedOperationError(
                f"myQLM operation references unknown classical bit index {classical_index}"
            ) from exc
