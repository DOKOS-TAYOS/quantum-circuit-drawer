"""Base adapter contracts for framework-to-IR conversion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR
from ..ir.packing import pack_operation_nodes
from ..ir.semantic import SemanticCircuitIR

OperationNode = OperationIR | MeasurementIR


class BaseAdapter(ABC):
    """Base contract for adapters that translate framework objects into IR."""

    framework_name: str

    @classmethod
    def explicit_framework_unavailable_reason(cls) -> str | None:
        """Return a user-facing reason when explicit framework selection is unavailable."""

        return None

    @classmethod
    @abstractmethod
    def can_handle(cls, circuit: object) -> bool:
        """Return whether this adapter recognizes the given circuit object."""

    @abstractmethod
    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        """Convert a framework object into the library's neutral ``CircuitIR``.

        Adapters should accept ``options`` as a forward-compatible mapping
        and ignore unknown keys they do not understand. The stable keys the
        public API guarantees today are ``"composite_mode"`` and
        ``"explicit_matrices"``.
        """

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR | None:
        """Optionally convert a framework object into semantic IR first.

        Adapters that do not override this method continue to work through the
        legacy ``to_ir(...)`` path without any behavior change.
        """

        del circuit, options
        return None

    def pack_operations(self, operations: Iterable[OperationNode]) -> tuple[LayerIR, ...]:
        """Pack operations into drawable layers without wire collisions.

        The packing logic respects every occupied slot reported by the
        operation, including control wires, classical conditions, and
        measurement targets.
        """

        return pack_operation_nodes(operations)
