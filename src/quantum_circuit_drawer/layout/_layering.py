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
