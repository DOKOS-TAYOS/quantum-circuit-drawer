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

    minimum_slot: int | None = None
    maximum_slot: int | None = None

    def include_wire(wire_id: str) -> None:
        nonlocal minimum_slot, maximum_slot
        slot_index = wire_order.get(wire_id)
        if slot_index is None:
            return
        if minimum_slot is None or slot_index < minimum_slot:
            minimum_slot = slot_index
        if maximum_slot is None or slot_index > maximum_slot:
            maximum_slot = slot_index

    for wire_id in operation.control_wires:
        include_wire(wire_id)
    for wire_id in operation.target_wires:
        include_wire(wire_id)
    for condition in operation.classical_conditions:
        for wire_id in condition.wire_ids:
            include_wire(wire_id)
    if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
        include_wire(operation.classical_target)

    if minimum_slot is None or maximum_slot is None:
        return ()

    return tuple(range(minimum_slot, maximum_slot + 1))
