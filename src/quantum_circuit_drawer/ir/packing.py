"""Shared packing helpers for converting flat operations into IR layers."""

from __future__ import annotations

from collections.abc import Iterable

from .circuit import LayerIR, OperationNode


def pack_operation_nodes(operations: Iterable[OperationNode]) -> tuple[LayerIR, ...]:
    """Pack operations into drawable layers without occupied-wire collisions."""

    layer_operations: list[list[OperationNode]] = []
    latest_layer_by_slot: dict[str, int] = {}
    for operation in operations:
        slots = tuple(dict.fromkeys(operation.occupied_wire_ids))
        target_layer = max((latest_layer_by_slot.get(slot, -1) for slot in slots), default=-1) + 1
        while len(layer_operations) <= target_layer:
            layer_operations.append([])
        layer_operations[target_layer].append(operation)
        for slot in slots:
            latest_layer_by_slot[slot] = target_layer
    return tuple(LayerIR(operations=layer) for layer in layer_operations)
