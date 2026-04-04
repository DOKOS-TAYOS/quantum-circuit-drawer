"""Adapter registration and lookup."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..exceptions import UnsupportedFrameworkError
from .base import BaseAdapter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AdapterRegistry:
    """Registry of framework adapters."""

    _adapter_types: dict[str, type[BaseAdapter]] = field(default_factory=dict)

    def register(self, adapter_type: type[BaseAdapter]) -> None:
        self._adapter_types[adapter_type.framework_name] = adapter_type

    def get(self, framework_name: str) -> BaseAdapter:
        self._ensure_defaults_registered()
        try:
            adapter = self._adapter_types[framework_name]()
        except KeyError as exc:
            available = ", ".join(sorted(self._adapter_types))
            raise UnsupportedFrameworkError(
                f"unsupported framework '{framework_name}'. Available adapters: {available}"
            ) from exc
        logger.debug(
            "Using explicit adapter %s for framework=%r", type(adapter).__name__, framework_name
        )
        return adapter

    def detect(self, circuit: object) -> BaseAdapter:
        self._ensure_defaults_registered()
        for adapter_type in self._adapter_types.values():
            if adapter_type.can_handle(circuit):
                adapter = adapter_type()
                logger.debug(
                    "Autodetected adapter %s for object type %r",
                    type(adapter).__name__,
                    type(circuit),
                )
                return adapter
        raise UnsupportedFrameworkError(
            f"could not autodetect a framework adapter for object of type {type(circuit)!r}"
        )

    def _ensure_defaults_registered(self) -> None:
        if self._adapter_types:
            return
        from .cirq_adapter import CirqAdapter
        from .cudaq_adapter import CudaqAdapter
        from .ir_adapter import IRAdapter
        from .pennylane_adapter import PennyLaneAdapter
        from .qiskit_adapter import QiskitAdapter

        for adapter_type in (IRAdapter, QiskitAdapter, CirqAdapter, PennyLaneAdapter, CudaqAdapter):
            self.register(adapter_type)


registry = AdapterRegistry()


def get_adapter(circuit: object, framework: str | None = None) -> BaseAdapter:
    """Return an adapter by explicit framework or autodetection."""

    adapter = registry.get(framework) if framework is not None else registry.detect(circuit)
    if framework is not None and not adapter.can_handle(circuit):
        raise UnsupportedFrameworkError(
            f"framework '{framework}' does not match object of type {type(circuit)!r}"
        )
    return adapter
