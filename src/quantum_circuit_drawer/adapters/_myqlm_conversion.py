"""Semantic conversion helpers for the MyQLM adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from ..config import UnsupportedPolicy
from ..diagnostics import DiagnosticSeverity, RenderDiagnostic
from ..exceptions import UnsupportedOperationError
from ..ir.operations import OperationKind
from ..ir.semantic import SemanticOperationIR
from ._helpers import (
    append_semantic_classical_conditions,
    canonical_gate_spec,
    normalized_detail_lines,
    semantic_provenance,
)
from ._myqlm_resolver import (
    _MyQLMCircuitImplementationLike,
    _MyQLMGateDefinitionLike,
    _MyQLMOpLike,
    classical_box_target_wires,
    classical_condition_for_operation,
    classical_target,
    control_count,
    gate_display_name,
    gate_parameters,
    operation_type_name,
    placeholder_display_name,
    placeholder_target_wires,
    remap_summary,
    safe_classical_condition_for_operation,
    subgate_spec,
    target_wire_ids,
    wire_id_for_index,
)


@dataclass(slots=True)
class MyQLMConversionContext:
    framework_name: str
    gate_definitions: Mapping[str, _MyQLMGateDefinitionLike]
    qubit_wire_ids: Mapping[int, str]
    classical_targets: Mapping[int, tuple[str, str]]
    composite_mode: str
    unsupported_policy: UnsupportedPolicy
    diagnostics: list[RenderDiagnostic]


def convert_operation(
    context: MyQLMConversionContext,
    operation: _MyQLMOpLike,
    *,
    location: tuple[int, ...],
    decomposition_origin: str | None,
    composite_label: str | None,
) -> list[SemanticOperationIR]:
    resolved_operation_type = operation_type_name(operation.type)
    try:
        if resolved_operation_type == "GATETYPE":
            return convert_gate_application(
                context,
                operation,
                location=location,
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
        if resolved_operation_type == "CLASSICCTRL":
            converted = convert_gate_application(
                context,
                operation,
                location=location,
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
            condition = classical_condition_for_operation(operation, context.classical_targets)
            return [
                replace(
                    append_semantic_classical_conditions(node, (condition,)),
                    hover_details=(
                        *node.hover_details,
                        f"classical control: {condition.expression}",
                    ),
                    provenance=semantic_provenance(
                        framework=context.framework_name,
                        native_name=node.provenance.native_name or node.name,
                        native_kind="classicctrl",
                        decomposition_origin=node.provenance.decomposition_origin,
                        composite_label=node.provenance.composite_label,
                        location=node.provenance.location,
                    ),
                )
                for node in converted
            ]
        if resolved_operation_type == "MEASURE":
            return convert_measurement(
                context,
                operation,
                location=location,
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
        if resolved_operation_type == "RESET":
            return convert_reset(
                context,
                operation,
                location=location,
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
        if resolved_operation_type == "REMAP":
            return convert_remap(
                context,
                operation,
                location=location,
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
        if resolved_operation_type in {"BREAK", "CLASSIC"}:
            return convert_classical_box(
                context,
                operation,
                operation_type=resolved_operation_type,
                location=location,
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
        raise UnsupportedOperationError(
            f"unsupported myQLM operation type '{resolved_operation_type.lower()}'"
        )
    except UnsupportedOperationError as exc:
        placeholder = recover_as_placeholder(
            context,
            operation,
            operation_type=resolved_operation_type,
            error=exc,
            location=location,
            decomposition_origin=decomposition_origin,
            composite_label=composite_label,
        )
        if placeholder is not None:
            return placeholder
        raise


def convert_gate_application(
    context: MyQLMConversionContext,
    operation: _MyQLMOpLike,
    *,
    location: tuple[int, ...],
    decomposition_origin: str | None,
    composite_label: str | None,
) -> list[SemanticOperationIR]:
    gate_key = operation.gate
    if gate_key is None:
        raise UnsupportedOperationError("myQLM gate operation is missing a gate definition")

    resolved_target_wires = target_wire_ids(operation.qbits, context.qubit_wire_ids)
    definition = context.gate_definitions.get(gate_key)
    display_name = gate_display_name(definition, gate_key)
    parameters = gate_parameters(definition)

    if definition is not None and definition.circuit_implementation is not None:
        implementation = definition.circuit_implementation
        ancilla_count = int(getattr(implementation, "ancillas", 0) or 0)
        if context.composite_mode == "expand" and ancilla_count == 0:
            nested_context = replace(context, qubit_wire_ids=resolved_target_wires)
            return expand_circuit_implementation(
                nested_context,
                implementation,
                location=location,
                decomposition_origin=display_name,
                composite_label=display_name,
            )
        if context.composite_mode == "expand" and ancilla_count > 0:
            context.diagnostics.append(
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
            compact_composite_operation(
                context,
                display_name=display_name,
                target_wires=tuple(resolved_target_wires.values()),
                parameters=parameters,
                location=location,
                ancilla_count=ancilla_count,
                effective_arity=int(
                    getattr(implementation, "nbqbits", len(resolved_target_wires)) or 0
                )
                or len(resolved_target_wires),
            )
        ]

    resolved_control_count = control_count(definition)
    if resolved_control_count > 0:
        ordered_wires = tuple(resolved_target_wires.values())
        if len(ordered_wires) <= resolved_control_count:
            raise UnsupportedOperationError(
                f"myQLM controlled gate '{display_name}' has no target wires after controls"
            )
        base_gate_spec = subgate_spec(definition, context.gate_definitions)
        return [
            SemanticOperationIR(
                kind=OperationKind.CONTROLLED_GATE,
                name=base_gate_spec.label,
                canonical_family=base_gate_spec.family,
                target_wires=ordered_wires[resolved_control_count:],
                control_wires=ordered_wires[:resolved_control_count],
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
                    framework=context.framework_name,
                    native_name=display_name,
                    native_kind="controlled_gate",
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
                    location=location,
                ),
            )
        ]

    canonical_gate = canonical_gate_spec(display_name)
    ordered_wires = tuple(resolved_target_wires.values())
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
                    framework=context.framework_name,
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
                framework=context.framework_name,
                native_name=display_name,
                native_kind="gate",
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
                location=location,
            ),
        )
    ]


def expand_circuit_implementation(
    context: MyQLMConversionContext,
    implementation: _MyQLMCircuitImplementationLike,
    *,
    location: tuple[int, ...],
    decomposition_origin: str,
    composite_label: str,
) -> list[SemanticOperationIR]:
    ancilla_count = int(getattr(implementation, "ancillas", 0) or 0)
    required_qubits = int(getattr(implementation, "nbqbits", len(context.qubit_wire_ids)) or 0)
    if ancilla_count > 0:
        raise UnsupportedOperationError(
            "myQLM composite operations with ancillas must be rendered as compact boxes"
        )
    if required_qubits > len(context.qubit_wire_ids):
        raise UnsupportedOperationError(
            "myQLM composite operation requires more qubits than the enclosing call provides"
        )

    nested_wire_ids = {index: context.qubit_wire_ids[index] for index in range(required_qubits)}
    nested_context = replace(context, qubit_wire_ids=nested_wire_ids)
    expanded: list[SemanticOperationIR] = []
    for nested_index, nested_operation in enumerate(implementation.ops):
        expanded.extend(
            convert_operation(
                nested_context,
                nested_operation,
                location=(*location, nested_index),
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
            )
        )
    return expanded


def compact_composite_operation(
    context: MyQLMConversionContext,
    *,
    display_name: str,
    target_wires: tuple[str, ...],
    parameters: tuple[object, ...],
    location: tuple[int, ...],
    ancilla_count: int = 0,
    effective_arity: int | None = None,
) -> SemanticOperationIR:
    hover_details: list[str] = [f"native: {display_name}", f"composite: {display_name}"]
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
            framework=context.framework_name,
            native_name=display_name,
            native_kind="composite",
            composite_label=display_name,
            location=location,
        ),
    )


def convert_measurement(
    context: MyQLMConversionContext,
    operation: _MyQLMOpLike,
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
        resolved_classical_target, bit_label = classical_target(
            cbit_index, context.classical_targets
        )
        converted_measurements.append(
            SemanticOperationIR(
                kind=OperationKind.MEASUREMENT,
                name="M",
                target_wires=(wire_id_for_index(qubit_index, context.qubit_wire_ids),),
                classical_target=resolved_classical_target,
                hover_details=normalized_detail_lines(
                    f"classical target: {bit_label}",
                    (
                        f"decomposed from: {decomposition_origin}"
                        if decomposition_origin is not None
                        else None
                    ),
                ),
                provenance=semantic_provenance(
                    framework=context.framework_name,
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


def convert_reset(
    context: MyQLMConversionContext,
    operation: _MyQLMOpLike,
    *,
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
        classical_target(classical_index, context.classical_targets)[1]
        for classical_index in classical_bits
    )
    hover_details = normalized_detail_lines(
        "native: RESET",
        (f"classical bits: {', '.join(classical_bit_labels)}" if classical_bit_labels else None),
        (f"formula raw: {formula_text}" if formula_text else None),
        (f"decomposed from: {decomposition_origin}" if decomposition_origin is not None else None),
    )
    return [
        SemanticOperationIR(
            kind=OperationKind.GATE,
            name="RESET",
            target_wires=(wire_id_for_index(qubit_index, context.qubit_wire_ids),),
            hover_details=hover_details,
            provenance=semantic_provenance(
                framework=context.framework_name,
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


def convert_remap(
    context: MyQLMConversionContext,
    operation: _MyQLMOpLike,
    *,
    location: tuple[int, ...],
    decomposition_origin: str | None,
    composite_label: str | None,
) -> list[SemanticOperationIR]:
    resolved_target_wires = tuple(target_wire_ids(operation.qbits, context.qubit_wire_ids).values())
    if not resolved_target_wires:
        raise UnsupportedOperationError("myQLM REMAP operation does not reference any qubits")
    hover_details = normalized_detail_lines(
        "native: REMAP",
        remap_summary(operation, context.qubit_wire_ids),
        (f"decomposed from: {decomposition_origin}" if decomposition_origin is not None else None),
    )
    return [
        SemanticOperationIR(
            kind=OperationKind.GATE,
            name="REMAP",
            label="REMAP",
            target_wires=resolved_target_wires,
            hover_details=hover_details,
            provenance=semantic_provenance(
                framework=context.framework_name,
                native_name="REMAP",
                native_kind="remap",
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
                location=location,
            ),
        )
    ]


def convert_classical_box(
    context: MyQLMConversionContext,
    operation: _MyQLMOpLike,
    *,
    operation_type: str,
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
        classical_target(classical_index, context.classical_targets)
        for classical_index in classical_bits
    )
    bit_labels = tuple(bit_label for _, bit_label in resolved_targets)
    resolved_target_wires = classical_box_target_wires(
        operation_type=operation_type,
        resolved_targets=resolved_targets,
    )
    condition = safe_classical_condition_for_operation(operation, context.classical_targets)
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
        (f"decomposed from: {decomposition_origin}" if decomposition_origin is not None else None),
    )

    semantic_operation = SemanticOperationIR(
        kind=OperationKind.GATE,
        name=operation_type,
        label=operation_type,
        target_wires=resolved_target_wires,
        hover_details=hover_details,
        provenance=semantic_provenance(
            framework=context.framework_name,
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


def recover_as_placeholder(
    context: MyQLMConversionContext,
    operation: _MyQLMOpLike,
    *,
    operation_type: str,
    error: UnsupportedOperationError,
    location: tuple[int, ...],
    decomposition_origin: str | None,
    composite_label: str | None,
) -> list[SemanticOperationIR] | None:
    if context.unsupported_policy is not UnsupportedPolicy.PLACEHOLDER:
        return None
    if operation_type == "MEASURE":
        return None

    resolved_target_wires = placeholder_target_wires(operation, context.qubit_wire_ids)
    if not resolved_target_wires:
        return None

    display_name = placeholder_display_name(
        operation,
        operation_type=operation_type,
        gate_definitions=context.gate_definitions,
    )
    context.diagnostics.append(
        RenderDiagnostic(
            code="unsupported_operation_placeholder",
            message=(
                f"Rendered unsupported myQLM operation {display_name!r} as a placeholder: {error}"
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
                framework=context.framework_name,
                native_name=display_name,
                native_kind=operation_type.lower(),
                decomposition_origin=decomposition_origin,
                composite_label=composite_label,
                location=(*location, placeholder_index),
            ),
            metadata={"display_subtitle": "unsupported"},
        )
        for placeholder_index, wire_id in enumerate(resolved_target_wires)
    ]
