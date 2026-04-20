"""Passthrough adapter for CircuitIR objects."""

from __future__ import annotations

from collections.abc import Mapping

from ..ir.circuit import CircuitIR
from .base import BaseAdapter


class IRAdapter(BaseAdapter):
    """Treat CircuitIR as an already-adapted circuit."""

    framework_name = "ir"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, CircuitIR)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        del options
        if not isinstance(circuit, CircuitIR):
            raise TypeError("IRAdapter expects CircuitIR instances")
        return circuit
