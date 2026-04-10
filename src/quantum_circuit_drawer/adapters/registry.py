"""Registration, autodetection, and explicit lookup for framework adapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..exceptions import UnsupportedFrameworkError
from .base import BaseAdapter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AdapterRegistry:
    """Registry of adapter types, with lazy registration of built-in adapters."""

    _adapter_types: dict[str, type[BaseAdapter]] = field(default_factory=dict)

    def register(self, adapter_type: type[BaseAdapter]) -> None:
        """Register one adapter class under its declared framework name."""

        self._adapter_types[adapter_type.framework_name] = adapter_type
        logger.debug(
            "Registered adapter %s for framework=%r",
            adapter_type.__name__,
            adapter_type.framework_name,
        )

    def get(self, framework_name: str) -> BaseAdapter:
        """Instantiate the adapter registered for one explicit framework name."""

        self._ensure_defaults_registered()
        adapter_type = self._adapter_type_for_framework(framework_name)
        adapter = adapter_type()
        logger.debug(
            "Using explicit adapter %s for framework=%r", type(adapter).__name__, framework_name
        )
        return adapter

    def detect(self, circuit: object) -> BaseAdapter:
        """Instantiate the first built-in adapter that recognizes ``circuit``."""

        adapter_type = self.detect_adapter_type(circuit)
        adapter = adapter_type()
        logger.debug(
            "Autodetected adapter %s for object type %r",
            type(adapter).__name__,
            type(circuit),
        )
        return adapter

    def detect_adapter_type(self, circuit: object) -> type[BaseAdapter]:
        """Return the adapter class that can handle ``circuit``."""

        self._ensure_defaults_registered()
        for adapter_type in self._adapter_types.values():
            if adapter_type.can_handle(circuit):
                return adapter_type
        raise UnsupportedFrameworkError(
            f"could not autodetect a framework adapter for object of type {type(circuit)!r}"
        )

    def detect_framework_name(self, circuit: object) -> str | None:
        """Return the detected framework name, or ``None`` if none match."""

        try:
            return self.detect_adapter_type(circuit).framework_name
        except UnsupportedFrameworkError:
            return None

    def available_frameworks(self) -> tuple[str, ...]:
        """Return the registered framework names in registration order."""

        self._ensure_defaults_registered()
        return tuple(self._adapter_types)

    def _adapter_type_for_framework(self, framework_name: str) -> type[BaseAdapter]:
        try:
            return self._adapter_types[framework_name]
        except KeyError as exc:
            available = ", ".join(sorted(self.available_frameworks()))
            raise UnsupportedFrameworkError(
                f"unsupported framework '{framework_name}'. Available adapters: {available}"
            ) from exc

    def _ensure_defaults_registered(self) -> None:
        if self._adapter_types:
            return
        for adapter_type in _default_adapter_types():
            self.register(adapter_type)


def _default_adapter_types() -> tuple[type[BaseAdapter], ...]:
    from .cirq_adapter import CirqAdapter
    from .cudaq_adapter import CudaqAdapter
    from .ir_adapter import IRAdapter
    from .myqlm_adapter import MyQLMAdapter
    from .pennylane_adapter import PennyLaneAdapter
    from .qiskit_adapter import QiskitAdapter

    return (IRAdapter, QiskitAdapter, CirqAdapter, PennyLaneAdapter, MyQLMAdapter, CudaqAdapter)


registry = AdapterRegistry()


def get_adapter(circuit: object, framework: str | None = None) -> BaseAdapter:
    """Return an adapter by explicit framework request or autodetection.

    When ``framework`` is provided, mismatches are reported clearly instead of
    silently falling back to autodetection.
    """

    if framework is None:
        return registry.detect(circuit)

    adapter = registry.get(framework)
    if adapter.can_handle(circuit):
        return adapter

    detected_framework = registry.detect_framework_name(circuit)
    if detected_framework is not None:
        raise UnsupportedFrameworkError(
            f"requested framework '{framework}' does not match object of type {type(circuit)!r}; "
            f"autodetected '{detected_framework}'"
        )
    raise UnsupportedFrameworkError(
        f"requested framework '{framework}' does not match object of type {type(circuit)!r}"
    )
