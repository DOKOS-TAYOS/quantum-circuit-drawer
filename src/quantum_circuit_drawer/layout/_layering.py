"""Shared layer normalization helpers for 2D and 3D layout engines."""

from __future__ import annotations

from ..ir.circuit import CircuitIR, LayerIR
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
        for operation in layer.operations:
            span_slots = operation_draw_span_slots(operation, wire_order)
            target_layer = (
                max((latest_layer_by_slot.get(slot, -1) for slot in span_slots), default=-1) + 1
            )
            while len(drawable_layers) <= target_layer:
                drawable_layers.append([])
            drawable_layers[target_layer].append(operation)
            for slot in span_slots:
                latest_layer_by_slot[slot] = target_layer
        normalized_layers.extend(
            LayerIR(operations=tuple(drawable_layer)) for drawable_layer in drawable_layers
        )
    return tuple(normalized_layers)


def operation_draw_span_slots(
    operation: OperationNode,
    wire_order: dict[str, int],
) -> tuple[int, ...]:
    """Return the occupied draw slots for an operation, including classical conditions."""

    involved_wires = list(operation.control_wires) + list(operation.target_wires)
    for condition in operation.classical_conditions:
        involved_wires.extend(condition.wire_ids)
    if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
        involved_wires.append(operation.classical_target)

    slot_indexes = sorted(
        wire_order[wire_id] for wire_id in involved_wires if wire_id in wire_order
    )
    if not slot_indexes:
        return ()

    return tuple(range(slot_indexes[0], slot_indexes[-1] + 1))
