"""Qiskit control-flow conversion helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace

from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.operations import OperationKind
from ..ir.semantic import SemanticOperationIR, semantic_operation_id_from_location
from ._helpers import (
    append_semantic_classical_conditions,
    normalized_detail_lines,
    semantic_provenance,
)

CONTROL_FLOW_LABELS: dict[str, str] = {
    "if": "IF",
    "else": "ELSE",
    "if_else": "IF/ELSE",
    "switch_case": "SWITCH",
    "for_loop": "FOR",
    "while_loop": "WHILE",
}
COMPACT_CONTROL_FLOW_SUBTITLE_FONT_SCALE = 0.62


def convert_if_else(
    *,
    framework_name: str,
    operation: object,
    qubits: tuple[object, ...],
    clbits: tuple[object, ...],
    qubit_ids: dict[object, str],
    classical_targets: dict[object, tuple[str, str]],
    register_targets: dict[object, tuple[str, str]],
    composite_mode: str,
    location: tuple[int, ...] = (),
    explicit_matrices: bool = True,
    condition_from_qiskit: Callable[
        [object, dict[object, tuple[str, str]], dict[object, tuple[str, str]]],
        ClassicalConditionIR,
    ],
    convert_compact_control_flow: Callable[..., list[SemanticOperationIR]],
    control_flow_hover_details: Callable[..., tuple[str, ...]],
    instruction_converter: Callable[..., list[SemanticOperationIR]],
) -> list[SemanticOperationIR]:
    blocks = tuple(getattr(operation, "blocks", ()) or ())
    if not blocks:
        return []

    true_block = blocks[0]
    false_block = blocks[1] if len(blocks) > 1 else None
    try:
        condition = condition_from_qiskit(
            getattr(operation, "condition", None),
            classical_targets,
            register_targets,
        )
    except UnsupportedOperationError:
        return convert_compact_control_flow(
            operation=operation,
            name="if_else",
            qubits=qubits,
            qubit_ids=qubit_ids,
            classical_targets=classical_targets,
            register_targets=register_targets,
            location=location,
            label="IF",
        )

    condition_details = normalized_detail_lines(f"condition: {condition.expression}")
    hover_details = control_flow_hover_details(
        name="if_else",
        operation=operation,
        condition_details=condition_details,
    )
    base_group_id = semantic_operation_id_from_location(location)
    converted_operations = _convert_grouped_control_flow_block(
        framework_name=framework_name,
        operation=operation,
        block=true_block,
        block_name="true_block",
        branch_location=(0,),
        qubits=qubits,
        clbits=clbits,
        qubit_ids=qubit_ids,
        classical_targets=classical_targets,
        composite_mode=composite_mode,
        location=location,
        explicit_matrices=explicit_matrices,
        instruction_converter=instruction_converter,
        group_metadata=_control_flow_group_metadata(
            group_id=f"{base_group_id}:if",
            label=CONTROL_FLOW_LABELS["if"],
            native_name="if_else",
            details=hover_details,
            conditions=(condition,),
        ),
        operation_classical_conditions=(condition,),
    )
    if false_block is not None:
        converted_operations.extend(
            _convert_grouped_control_flow_block(
                framework_name=framework_name,
                operation=operation,
                block=false_block,
                block_name="false_block",
                branch_location=(1,),
                qubits=qubits,
                clbits=clbits,
                qubit_ids=qubit_ids,
                classical_targets=classical_targets,
                composite_mode=composite_mode,
                location=location,
                explicit_matrices=explicit_matrices,
                instruction_converter=instruction_converter,
                group_metadata=_control_flow_group_metadata(
                    group_id=f"{base_group_id}:else",
                    label=CONTROL_FLOW_LABELS["else"],
                    native_name="if_else",
                    details=hover_details,
                    dependencies=_condition_wire_ids((condition,)),
                ),
            )
        )
    return converted_operations


def convert_compact_control_flow(
    *,
    framework_name: str,
    operation: object,
    name: str,
    qubits: tuple[object, ...],
    qubit_ids: dict[object, str],
    classical_targets: dict[object, tuple[str, str]],
    register_targets: dict[object, tuple[str, str]],
    location: tuple[int, ...],
    label: str | None = None,
    compact_control_flow_conditions: Callable[
        ..., tuple[tuple[ClassicalConditionIR, ...], tuple[str, ...]]
    ],
    control_flow_hover_details: Callable[..., tuple[str, ...]],
) -> list[SemanticOperationIR]:
    target_wires = tuple(qubit_ids[qubit] for qubit in qubits)
    if not target_wires:
        raise UnsupportedOperationError(f"Qiskit control-flow '{name}' has no drawable targets")

    classical_conditions, condition_details = compact_control_flow_conditions(
        name=name,
        operation=operation,
        classical_targets=classical_targets,
        register_targets=register_targets,
    )
    hover_details = control_flow_hover_details(
        name=name,
        operation=operation,
        condition_details=condition_details,
    )
    resolved_label = label or CONTROL_FLOW_LABELS[name]
    metadata: dict[str, object] = {"qiskit_control_flow": name}
    static_subtitle = compact_control_flow_static_subtitle(
        name=name,
        condition_details=condition_details,
        hover_details=hover_details,
    )
    if static_subtitle is not None:
        metadata["display_subtitle"] = static_subtitle
        metadata["subtitle_font_scale"] = COMPACT_CONTROL_FLOW_SUBTITLE_FONT_SCALE
    return [
        SemanticOperationIR(
            kind=OperationKind.GATE,
            name=resolved_label,
            label=resolved_label,
            target_wires=target_wires,
            classical_conditions=classical_conditions,
            hover_details=hover_details,
            provenance=semantic_provenance(
                framework=framework_name,
                native_name=name,
                native_kind="control_flow",
                location=location,
            ),
            metadata=metadata,
        )
    ]


def convert_loop_control_flow(
    *,
    framework_name: str,
    operation: object,
    name: str,
    qubits: tuple[object, ...],
    clbits: tuple[object, ...],
    qubit_ids: dict[object, str],
    classical_targets: dict[object, tuple[str, str]],
    register_targets: dict[object, tuple[str, str]],
    composite_mode: str,
    location: tuple[int, ...],
    explicit_matrices: bool,
    compact_control_flow_conditions: Callable[
        ..., tuple[tuple[ClassicalConditionIR, ...], tuple[str, ...]]
    ],
    control_flow_hover_details: Callable[..., tuple[str, ...]],
    instruction_converter: Callable[..., list[SemanticOperationIR]],
) -> list[SemanticOperationIR]:
    """Expand Qiskit loop bodies and mark them as one drawable control-flow block."""

    blocks = tuple(getattr(operation, "blocks", ()) or ())
    if not blocks:
        return convert_compact_control_flow(
            framework_name=framework_name,
            operation=operation,
            name=name,
            qubits=qubits,
            qubit_ids=qubit_ids,
            classical_targets=classical_targets,
            register_targets=register_targets,
            location=location,
            compact_control_flow_conditions=compact_control_flow_conditions,
            control_flow_hover_details=control_flow_hover_details,
        )

    body = blocks[0]
    if len(body.qubits) != len(qubits):
        raise UnsupportedOperationError(
            f"Qiskit {name} body qubit mapping mismatch: "
            f"expected {len(body.qubits)} inner qubits, received {len(qubits)} outer qubits"
        )
    if len(body.clbits) != len(clbits):
        raise UnsupportedOperationError(
            f"Qiskit {name} body clbit mapping mismatch: "
            f"expected {len(body.clbits)} inner clbits, received {len(clbits)} outer clbits"
        )

    nested_qubit_ids = {
        inner_qubit: qubit_ids[outer_qubit]
        for inner_qubit, outer_qubit in zip(body.qubits, qubits, strict=True)
    }
    nested_classical_targets = {
        inner_clbit: classical_targets[outer_clbit]
        for inner_clbit, outer_clbit in zip(body.clbits, clbits, strict=True)
        if outer_clbit in classical_targets
    }
    classical_conditions, condition_details = compact_control_flow_conditions(
        name=name,
        operation=operation,
        classical_targets=classical_targets,
        register_targets=register_targets,
    )
    hover_details = control_flow_hover_details(
        name=name,
        operation=operation,
        condition_details=condition_details,
    )
    label = control_flow_group_display_label(name, operation)
    group_metadata = _control_flow_group_metadata(
        group_id=semantic_operation_id_from_location(location),
        label=label,
        native_name=name,
        details=hover_details,
        hover_label=CONTROL_FLOW_LABELS[name],
        conditions=classical_conditions if name == "while_loop" else (),
    )

    converted_operations: list[SemanticOperationIR] = []
    for nested_index, inner_entry in enumerate(body.data):
        nested_operations = instruction_converter(
            inner_entry,
            nested_qubit_ids,
            nested_classical_targets,
            register_targets={},
            composite_mode=composite_mode,
            location=(*location, nested_index),
            explicit_matrices=explicit_matrices,
            decomposition_origin=name,
            composite_label=CONTROL_FLOW_LABELS[name],
        )
        converted_operations.extend(
            _with_control_flow_group_metadata(
                nested_operation,
                group_metadata=group_metadata,
                fallback_framework=framework_name,
                fallback_location=(*location, nested_index),
            )
            for nested_operation in nested_operations
        )
    return converted_operations


def _convert_grouped_control_flow_block(
    *,
    framework_name: str,
    operation: object,
    block: object,
    block_name: str,
    branch_location: tuple[int, ...],
    qubits: tuple[object, ...],
    clbits: tuple[object, ...],
    qubit_ids: dict[object, str],
    classical_targets: dict[object, tuple[str, str]],
    composite_mode: str,
    location: tuple[int, ...],
    explicit_matrices: bool,
    instruction_converter: Callable[..., list[SemanticOperationIR]],
    group_metadata: dict[str, object],
    operation_classical_conditions: tuple[ClassicalConditionIR, ...] = (),
) -> list[SemanticOperationIR]:
    nested_qubit_ids, nested_classical_targets = _nested_block_wire_maps(
        block=block,
        block_name=block_name,
        name="if_else",
        qubits=qubits,
        clbits=clbits,
        qubit_ids=qubit_ids,
        classical_targets=classical_targets,
    )
    converted_operations: list[SemanticOperationIR] = []
    for nested_index, inner_entry in enumerate(getattr(block, "data", ()) or ()):
        nested_operations = instruction_converter(
            inner_entry,
            nested_qubit_ids,
            nested_classical_targets,
            register_targets={},
            composite_mode=composite_mode,
            location=(*location, *branch_location, nested_index),
            explicit_matrices=explicit_matrices,
            decomposition_origin="if_else",
            composite_label=str(group_metadata["label"]),
        )
        if operation_classical_conditions:
            nested_operations = [
                append_semantic_classical_conditions(
                    nested_operation,
                    operation_classical_conditions,
                )
                for nested_operation in nested_operations
            ]
        converted_operations.extend(
            _with_control_flow_group_metadata(
                nested_operation,
                group_metadata=group_metadata,
                fallback_framework=framework_name,
                fallback_location=(*location, *branch_location, nested_index),
                suppress_classical_condition_connections=bool(operation_classical_conditions),
            )
            for nested_operation in nested_operations
        )
    return converted_operations


def _nested_block_wire_maps(
    *,
    block: object,
    block_name: str,
    name: str,
    qubits: tuple[object, ...],
    clbits: tuple[object, ...],
    qubit_ids: dict[object, str],
    classical_targets: dict[object, tuple[str, str]],
) -> tuple[dict[object, str], dict[object, tuple[str, str]]]:
    block_qubits = tuple(getattr(block, "qubits", ()) or ())
    block_clbits = tuple(getattr(block, "clbits", ()) or ())
    if len(block_qubits) != len(qubits):
        raise UnsupportedOperationError(
            f"Qiskit {name} {block_name} qubit mapping mismatch: "
            f"expected {len(block_qubits)} inner qubits, received {len(qubits)} outer qubits"
        )
    if len(block_clbits) != len(clbits):
        raise UnsupportedOperationError(
            f"Qiskit {name} {block_name} clbit mapping mismatch: "
            f"expected {len(block_clbits)} inner clbits, received {len(clbits)} outer clbits"
        )
    nested_qubit_ids = {
        inner_qubit: qubit_ids[outer_qubit]
        for inner_qubit, outer_qubit in zip(block_qubits, qubits, strict=True)
    }
    nested_classical_targets = {
        inner_clbit: classical_targets[outer_clbit]
        for inner_clbit, outer_clbit in zip(block_clbits, clbits, strict=True)
        if outer_clbit in classical_targets
    }
    return nested_qubit_ids, nested_classical_targets


def compact_control_flow_conditions(
    *,
    name: str,
    operation: object,
    classical_targets: dict[object, tuple[str, str]],
    register_targets: dict[object, tuple[str, str]],
    condition_from_qiskit: Callable[
        [object, dict[object, tuple[str, str]], dict[object, tuple[str, str]]],
        ClassicalConditionIR,
    ],
    switch_target_from_qiskit: Callable[
        [object, dict[object, tuple[str, str]], dict[object, tuple[str, str]]],
        tuple[ClassicalConditionIR, str],
    ],
    native_text: Callable[[object], str],
) -> tuple[tuple[ClassicalConditionIR, ...], tuple[str, ...]]:
    if name in {"if_else", "while_loop"}:
        condition_source = getattr(operation, "condition", None)
        if condition_source is None:
            return (), ()
        try:
            condition = condition_from_qiskit(
                condition_source,
                classical_targets,
                register_targets,
            )
        except UnsupportedOperationError:
            return (), normalized_detail_lines(f"condition: {native_text(condition_source)}")
        return (condition,), normalized_detail_lines(f"condition: {condition.expression}")

    if name == "switch_case":
        target_source = getattr(operation, "target", None)
        if target_source is None:
            return (), ()
        try:
            condition, target_text = switch_target_from_qiskit(
                target_source,
                classical_targets,
                register_targets,
            )
        except UnsupportedOperationError:
            return (), normalized_detail_lines(f"target: {native_text(target_source)}")
        return (condition,), normalized_detail_lines(f"target: {target_text}")

    return (), ()


def compact_control_flow_static_subtitle(
    *,
    name: str,
    condition_details: Sequence[str],
    hover_details: Sequence[str],
) -> str | None:
    if name != "switch_case":
        return None
    target = _detail_suffix(condition_details, "target: ")
    cases = _detail_suffix(hover_details, "cases: ")
    if target is None:
        return f"cases: {cases}" if cases is not None else None
    if cases is None:
        return target
    return f"{target}: {cases}"


def control_flow_hover_details(
    *,
    name: str,
    operation: object,
    condition_details: Sequence[str],
    native_text: Callable[[object], str],
) -> tuple[str, ...]:
    details: list[str] = [f"control flow: {name}", *condition_details]
    if name == "if_else":
        true_ops, false_ops = if_else_block_sizes(operation)
        if false_ops is None:
            details.append("branches: true only")
            details.append(f"block ops: true={true_ops}")
        else:
            details.append("branches: true, false")
            details.append(f"block ops: true={true_ops}, false={false_ops}")
    elif name == "switch_case":
        case_summary = switch_case_summary(operation, native_text=native_text)
        if case_summary is not None:
            details.append(f"cases: {case_summary}")
        details.append(f"case count: {len(switch_case_values(operation))}")
    elif name == "for_loop":
        iteration_summary = for_loop_iteration_summary(operation, native_text=native_text)
        if iteration_summary is not None:
            details.append(f"iteration: {iteration_summary}")
        details.append(f"body ops: {control_flow_body_size(operation)}")
    elif name == "while_loop":
        details.append(f"body ops: {control_flow_body_size(operation)}")
    return normalized_detail_lines(*details)


def switch_case_summary(
    operation: object,
    *,
    native_text: Callable[[object], str],
) -> str | None:
    values = switch_case_values(operation)
    if not values:
        return None

    formatted_values = [
        switch_case_value_text(value, native_text=native_text) for value in values[:4]
    ]
    if len(values) > 4:
        formatted_values.append("...")
    return ", ".join(formatted_values)


def switch_case_values(operation: object) -> tuple[object, ...]:
    cases_getter = getattr(operation, "cases", None)
    if callable(cases_getter):
        return tuple(cases_getter())
    cases_specifier = getattr(operation, "cases_specifier", None)
    if callable(cases_specifier):
        return tuple(case_value for case_value, _ in cases_specifier())
    return ()


def if_else_block_sizes(operation: object) -> tuple[int, int | None]:
    blocks = tuple(getattr(operation, "blocks", ()) or ())
    true_ops = operation_block_size(blocks[0]) if blocks else 0
    false_block = blocks[1] if len(blocks) > 1 else None
    false_ops = operation_block_size(false_block) if false_block is not None else None
    return true_ops, false_ops


def control_flow_body_size(operation: object) -> int:
    blocks = tuple(getattr(operation, "blocks", ()) or ())
    if not blocks:
        return 0
    return operation_block_size(blocks[0])


def operation_block_size(block: object | None) -> int:
    if block is None:
        return 0
    data = tuple(getattr(block, "data", ()) or ())
    return len(data)


def switch_case_value_text(
    value: object,
    *,
    native_text: Callable[[object], str],
) -> str:
    text = native_text(value)
    return "default" if text == "<default case>" else text


def for_loop_iteration_summary(
    operation: object,
    *,
    native_text: Callable[[object], str],
) -> str | None:
    params = tuple(getattr(operation, "params", ()) or ())
    indexset = getattr(operation, "indexset", None)
    if indexset is None and params:
        indexset = params[0]
    loop_parameter = getattr(operation, "loop_parameter", None)
    if loop_parameter is None and len(params) > 1:
        loop_parameter = params[1]
    if indexset is None and loop_parameter is None:
        return None
    indexset_text = native_text(indexset) if indexset is not None else "unknown"
    if loop_parameter is None:
        return indexset_text
    return f"{native_text(loop_parameter)} in {indexset_text}"


def _detail_suffix(details: Sequence[str], prefix: str) -> str | None:
    for detail in details:
        if detail.startswith(prefix):
            suffix = detail[len(prefix) :].strip()
            return suffix or None
    return None


def control_flow_group_display_label(name: str, operation: object) -> str:
    if name != "for_loop":
        return CONTROL_FLOW_LABELS[name]
    iteration_count = for_loop_iteration_count(operation)
    if iteration_count is None:
        return CONTROL_FLOW_LABELS[name]
    return f"{CONTROL_FLOW_LABELS[name]} x{iteration_count}"


def for_loop_iteration_count(operation: object) -> int | None:
    params = tuple(getattr(operation, "params", ()) or ())
    indexset = getattr(operation, "indexset", None)
    if indexset is None and params:
        indexset = params[0]
    if indexset is None:
        return None
    try:
        count = len(indexset)  # type: ignore[arg-type]
    except TypeError:
        return None
    return int(count) if count >= 0 else None


def _control_flow_group_metadata(
    *,
    group_id: str,
    label: str,
    native_name: str,
    details: tuple[str, ...],
    hover_label: str | None = None,
    conditions: tuple[ClassicalConditionIR, ...] = (),
    dependencies: tuple[str, ...] = (),
) -> dict[str, object]:
    resolved_dependencies = tuple(dict.fromkeys((*dependencies, *_condition_wire_ids(conditions))))
    return {
        "id": group_id,
        "label": label,
        "hover_label": hover_label or label,
        "native_name": native_name,
        "details": details,
        "conditions": conditions,
        "wire_dependencies": resolved_dependencies,
    }


def _condition_wire_ids(conditions: Sequence[ClassicalConditionIR]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(wire_id for condition in conditions for wire_id in condition.wire_ids)
    )


def _wire_dependency_metadata(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(wire_id) for wire_id in value if str(wire_id))


def _with_control_flow_group_metadata(
    operation: SemanticOperationIR,
    *,
    group_metadata: dict[str, object],
    fallback_framework: str,
    fallback_location: tuple[int, ...],
    suppress_classical_condition_connections: bool = False,
) -> SemanticOperationIR:
    provenance = operation.provenance
    if not provenance.location:
        provenance = replace(provenance, location=fallback_location)
    if provenance.framework is None:
        provenance = replace(provenance, framework=fallback_framework)
    if provenance.composite_label is None:
        provenance = replace(
            provenance,
            composite_label=str(group_metadata.get("hover_label") or group_metadata["label"]),
        )
    if provenance.decomposition_origin is None:
        provenance = replace(provenance, decomposition_origin=str(group_metadata["native_name"]))
    dependencies = tuple(
        dict.fromkeys(
            (
                *_wire_dependency_metadata(operation.metadata.get("occupied_wire_dependencies")),
                *_wire_dependency_metadata(group_metadata.get("wire_dependencies")),
            )
        )
    )
    metadata = {
        **operation.metadata,
        "control_flow_group": dict(group_metadata),
    }
    if dependencies:
        metadata["occupied_wire_dependencies"] = dependencies
    if suppress_classical_condition_connections:
        metadata["suppress_classical_condition_connections"] = True
    return replace(operation, provenance=provenance, metadata=metadata)
