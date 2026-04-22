"""Qiskit control-flow conversion helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.operations import OperationKind
from ..ir.semantic import SemanticOperationIR
from ._helpers import (
    append_semantic_classical_conditions,
    normalized_detail_lines,
    semantic_provenance,
)

CONTROL_FLOW_LABELS: dict[str, str] = {
    "if_else": "IF/ELSE",
    "switch_case": "SWITCH",
    "for_loop": "FOR",
    "while_loop": "WHILE",
}


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
    instruction_converter: Callable[..., list[SemanticOperationIR]],
) -> list[SemanticOperationIR]:
    blocks = tuple(getattr(operation, "blocks", ()) or ())
    if not blocks:
        return []

    if len(blocks) > 1 and blocks[1] is not None:
        return convert_compact_control_flow(
            operation=operation,
            name="if_else",
            qubits=qubits,
            qubit_ids=qubit_ids,
            classical_targets=classical_targets,
            register_targets=register_targets,
            location=location,
        )

    true_block = blocks[0]
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
    if len(true_block.qubits) != len(qubits):
        raise UnsupportedOperationError(
            "Qiskit if_else true_block qubit mapping mismatch: "
            f"expected {len(true_block.qubits)} inner qubits, received {len(qubits)} outer qubits"
        )
    if len(true_block.clbits) != len(clbits):
        raise UnsupportedOperationError(
            "Qiskit if_else true_block clbit mapping mismatch: "
            f"expected {len(true_block.clbits)} inner clbits, received {len(clbits)} outer clbits"
        )
    nested_qubit_ids = {
        inner_qubit: qubit_ids[outer_qubit]
        for inner_qubit, outer_qubit in zip(true_block.qubits, qubits, strict=True)
    }
    nested_classical_targets = {
        inner_clbit: classical_targets[outer_clbit]
        for inner_clbit, outer_clbit in zip(true_block.clbits, clbits, strict=True)
        if outer_clbit in classical_targets
    }

    converted_operations: list[SemanticOperationIR] = []
    for nested_index, inner_entry in enumerate(true_block.data):
        converted_operations.extend(
            instruction_converter(
                inner_entry,
                nested_qubit_ids,
                nested_classical_targets,
                register_targets={},
                composite_mode=composite_mode,
                location=(*location, nested_index),
                explicit_matrices=explicit_matrices,
            )
        )
    return [
        append_semantic_classical_conditions(node, (condition,)) for node in converted_operations
    ]


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
            metadata={"qiskit_control_flow": name},
        )
    ]


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
