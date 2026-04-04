"""Base adapter definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR

OperationNode = OperationIR | MeasurementIR


class BaseAdapter(ABC):
    """Base contract for framework adapters."""

    framework_name: str

    @classmethod
    @abstractmethod
    def can_handle(cls, circuit: object) -> bool:
        """Return whether the adapter can handle the given circuit object."""

    @abstractmethod
    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        """Convert a framework circuit into CircuitIR."""

    def pack_operations(self, operations: Iterable[OperationNode]) -> tuple[LayerIR, ...]:
        """Pack operations while preserving temporal order across occupied wires."""

        layer_operations: list[list[OperationNode]] = []
        latest_layer_by_slot: dict[str, int] = {}
        for operation in operations:
            slots = tuple(dict.fromkeys(operation.occupied_wire_ids))
            target_layer = (
                max((latest_layer_by_slot.get(slot, -1) for slot in slots), default=-1) + 1
            )
            while len(layer_operations) <= target_layer:
                layer_operations.append([])
            layer_operations[target_layer].append(operation)
            for slot in slots:
                latest_layer_by_slot[slot] = target_layer
        return tuple(LayerIR(operations=layer) for layer in layer_operations)
