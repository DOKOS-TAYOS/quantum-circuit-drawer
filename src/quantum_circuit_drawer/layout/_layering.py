"""Shared layer normalization helpers for 2D and 3D layout engines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.classical_conditions import ClassicalConditionIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR

OperationNode = OperationIR | MeasurementIR


def normalize_draw_layers(circuit: CircuitIR) -> tuple[LayerIR, ...]:
    """Expand input layers into drawable layers without overlapping occupied spans."""

    wire_order = {wire.id: index for index, wire in enumerate(circuit.all_wires)}
    normalized_layers: list[LayerIR] = []
    for layer in circuit.layers:
        drawable_layers: list[list[OperationNode]] = []
        latest_layer_by_slot: dict[int, int] = {}
        operations = tuple(layer.operations)
        operation_index = 0
        while operation_index < len(operations):
            operation = operations[operation_index]
            group_id = _control_flow_group_id(operation)
            if group_id is None:
                _pack_single_operation(
                    operation,
                    drawable_layers=drawable_layers,
                    latest_layer_by_slot=latest_layer_by_slot,
                    span_slots=operation_draw_span_slots(operation, wire_order),
                )
                operation_index += 1
                continue

            group_operations: list[OperationNode] = []
            while operation_index < len(operations):
                grouped_operation = operations[operation_index]
                if _control_flow_group_id(grouped_operation) != group_id:
                    break
                group_operations.append(grouped_operation)
                operation_index += 1

            _pack_control_flow_group_operations(
                tuple(group_operations),
                drawable_layers=drawable_layers,
                latest_layer_by_slot=latest_layer_by_slot,
                wire_order=wire_order,
            )
        normalized_layers.extend(
            LayerIR(operations=tuple(drawable_layer)) for drawable_layer in drawable_layers
        )
    return tuple(normalized_layers)


def normalized_draw_circuit(circuit: CircuitIR) -> CircuitIR:
    """Return a circuit whose layers already match the drawable layer normalization."""

    return CircuitIR(
        quantum_wires=circuit.quantum_wires,
        classical_wires=circuit.classical_wires,
        layers=normalize_draw_layers(circuit),
        name=circuit.name,
        metadata=dict(circuit.metadata),
    )


def operation_draw_span_slots(
    operation: OperationNode,
    wire_order: dict[str, int],
) -> tuple[int, ...]:
    """Return the occupied draw slots for an operation, including classical conditions."""

    slots = [
        wire_order[wire_id] for wire_id in operation.occupied_wire_ids if wire_id in wire_order
    ]
    if not slots:
        return ()

    return tuple(range(min(slots), max(slots) + 1))


def _pack_control_flow_group_operations(
    operations: tuple[OperationNode, ...],
    *,
    drawable_layers: list[list[OperationNode]],
    latest_layer_by_slot: dict[int, int],
    wire_order: dict[str, int],
) -> None:
    if not operations:
        return

    ignored_wire_ids = _control_flow_group_dependency_wire_ids(operations[0])
    boundary_slots = _control_flow_group_boundary_span_slots(operations, wire_order)
    target_layer = (
        max((latest_layer_by_slot.get(slot, -1) for slot in boundary_slots), default=-1) + 1
    )
    local_layers = _pack_control_flow_group_local_layers(
        operations,
        wire_order=wire_order,
        ignored_wire_ids=ignored_wire_ids,
    )
    for local_layer_index, local_layer in enumerate(local_layers):
        resolved_layer = target_layer + local_layer_index
        while len(drawable_layers) <= resolved_layer:
            drawable_layers.append([])
        drawable_layers[resolved_layer].extend(local_layer)

    end_layer = target_layer + len(local_layers) - 1
    for slot in boundary_slots:
        latest_layer_by_slot[slot] = end_layer


def _pack_control_flow_group_local_layers(
    operations: tuple[OperationNode, ...],
    *,
    wire_order: dict[str, int],
    ignored_wire_ids: frozenset[str],
) -> tuple[tuple[OperationNode, ...], ...]:
    drawable_layers: list[list[OperationNode]] = []
    latest_layer_by_slot: dict[int, int] = {}
    latest_layer_by_sequence_key: dict[tuple[str, ...], int] = {}
    for operation in operations:
        sequence_key = _nested_control_flow_sequence_key(operation)
        minimum_layer = _minimum_layer_for_control_flow_sequence(
            sequence_key,
            latest_layer_by_sequence_key,
        )
        target_layer = _pack_single_operation(
            operation,
            drawable_layers=drawable_layers,
            latest_layer_by_slot=latest_layer_by_slot,
            span_slots=_local_control_flow_operation_span_slots(
                operation,
                wire_order=wire_order,
                ignored_wire_ids=ignored_wire_ids,
            ),
            minimum_layer=minimum_layer,
        )
        latest_layer_by_sequence_key[sequence_key] = max(
            target_layer,
            latest_layer_by_sequence_key.get(sequence_key, -1),
        )
    return tuple(tuple(drawable_layer) for drawable_layer in drawable_layers)


def _pack_single_operation(
    operation: OperationNode,
    *,
    drawable_layers: list[list[OperationNode]],
    latest_layer_by_slot: dict[int, int],
    span_slots: tuple[int, ...],
    minimum_layer: int = 0,
) -> int:
    target_layer = max(
        max((latest_layer_by_slot.get(slot, -1) for slot in span_slots), default=-1) + 1,
        minimum_layer,
    )
    while len(drawable_layers) <= target_layer:
        drawable_layers.append([])
    drawable_layers[target_layer].append(operation)
    for slot in span_slots:
        latest_layer_by_slot[slot] = target_layer
    return target_layer


def _minimum_layer_for_control_flow_sequence(
    sequence_key: tuple[str, ...],
    latest_layer_by_sequence_key: Mapping[tuple[str, ...], int],
) -> int:
    return (
        max(
            (
                latest_layer
                for key, latest_layer in latest_layer_by_sequence_key.items()
                if key != sequence_key
            ),
            default=-1,
        )
        + 1
    )


def _nested_control_flow_sequence_key(operation: OperationNode) -> tuple[str, ...]:
    stack_ids = _control_flow_group_stack_ids(operation.metadata)
    if len(stack_ids) <= 1:
        return ()
    return stack_ids[:-1]


def _local_control_flow_operation_span_slots(
    operation: OperationNode,
    *,
    wire_order: dict[str, int],
    ignored_wire_ids: frozenset[str],
) -> tuple[int, ...]:
    wire_ids = _local_control_flow_operation_wire_ids(
        operation,
        ignored_wire_ids=ignored_wire_ids,
    )
    slots = [wire_order[wire_id] for wire_id in wire_ids if wire_id in wire_order]
    if not slots:
        return ()
    return tuple(range(min(slots), max(slots) + 1))


def _local_control_flow_operation_wire_ids(
    operation: OperationNode,
    *,
    ignored_wire_ids: frozenset[str],
) -> tuple[str, ...]:
    classical_wire_ids = tuple(
        wire_id
        for condition in operation.classical_conditions
        for wire_id in condition.wire_ids
        if wire_id not in ignored_wire_ids
    )
    dependency_wire_ids = tuple(
        wire_id
        for wire_id in _wire_dependency_metadata(
            operation.metadata.get("occupied_wire_dependencies")
        )
        if wire_id not in ignored_wire_ids
    )
    occupied_wire_ids = tuple(
        dict.fromkeys(
            (
                *classical_wire_ids,
                *dependency_wire_ids,
                *operation.control_wires,
                *operation.target_wires,
            )
        )
    )
    if not isinstance(operation, MeasurementIR):
        return occupied_wire_ids
    classical_target = operation.classical_target
    assert classical_target is not None
    return tuple(dict.fromkeys((*occupied_wire_ids, classical_target)))


def _control_flow_group_boundary_span_slots(
    operations: tuple[OperationNode, ...],
    wire_order: dict[str, int],
) -> tuple[int, ...]:
    slots = [
        slot
        for operation in operations
        for slot in operation_draw_span_slots(operation, wire_order)
    ]
    quantum_slots = [
        wire_order[wire_id]
        for operation in operations
        for wire_id in (*operation.control_wires, *operation.target_wires)
        if wire_id in wire_order
    ]
    if quantum_slots:
        slots.extend(range(min(quantum_slots), max(quantum_slots) + 1))
    if not slots:
        return ()
    return tuple(dict.fromkeys(slots))


def _control_flow_group_id(operation: OperationNode) -> str | None:
    group_metadata = operation.metadata.get("control_flow_group")
    if not isinstance(group_metadata, Mapping):
        return None
    group_id = group_metadata.get("id")
    if isinstance(group_id, str) and group_id:
        return group_id
    return None


def _control_flow_group_stack_ids(metadata: Mapping[str, object]) -> tuple[str, ...]:
    stacked_groups = metadata.get("control_flow_groups")
    if isinstance(stacked_groups, Sequence) and not isinstance(stacked_groups, str | bytes):
        return tuple(
            str(group_id)
            for group in stacked_groups
            if isinstance(group, Mapping)
            and isinstance(group_id := group.get("id"), str)
            and group_id
        )

    group_metadata = metadata.get("control_flow_group")
    if isinstance(group_metadata, Mapping):
        group_id = group_metadata.get("id")
        if isinstance(group_id, str) and group_id:
            return (group_id,)
    return ()


def _control_flow_group_dependency_wire_ids(operation: OperationNode) -> frozenset[str]:
    group_metadata = operation.metadata.get("control_flow_group")
    if not isinstance(group_metadata, Mapping):
        return frozenset()

    dependency_wire_ids = set(_wire_dependency_metadata(group_metadata.get("wire_dependencies")))
    conditions = group_metadata.get("conditions")
    if isinstance(conditions, ClassicalConditionIR):
        dependency_wire_ids.update(conditions.wire_ids)
    elif isinstance(conditions, Sequence) and not isinstance(conditions, str | bytes):
        for condition in conditions:
            if isinstance(condition, ClassicalConditionIR):
                dependency_wire_ids.update(condition.wire_ids)
    return frozenset(dependency_wire_ids)


def _wire_dependency_metadata(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(wire_id) for wire_id in value if str(wire_id))
