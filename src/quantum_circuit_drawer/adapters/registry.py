"""Registration, autodetection, and explicit lookup for framework adapters."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Final

from ..exceptions import UnsupportedFrameworkError
from .base import BaseAdapter

logger = logging.getLogger(__name__)
_DEFAULT_FRAMEWORK_NAMES: Final[tuple[str, ...]] = (
    "ir",
    "qiskit",
    "cirq",
    "pennylane",
    "myqlm",
    "cudaq",
)


@dataclass(slots=True)
class AdapterRegistry:
    """Registry of adapter types, with lazy registration of built-in adapters."""

    _adapter_types: dict[str, type[BaseAdapter]] = field(default_factory=dict)
    _defaults_registered: bool = False

    def register(self, adapter_type: type[BaseAdapter], *, replace: bool = False) -> None:
        """Register one adapter class under its declared framework name."""

        validated_adapter_type = self._validate_adapter_type(adapter_type)
        framework_name = _normalized_framework_name(validated_adapter_type.framework_name)
        framework_already_exists = framework_name in self._adapter_types
        builtin_name_reserved = (
            framework_name in _DEFAULT_FRAMEWORK_NAMES and not self._defaults_registered
        )
        if (framework_already_exists or builtin_name_reserved) and not replace:
            raise ValueError(f"framework {framework_name!r} is already registered")
        self._adapter_types[framework_name] = validated_adapter_type
        logger.debug(
            "Registered adapter %s for framework=%r",
            validated_adapter_type.__name__,
            framework_name,
        )

    def get(self, framework_name: str) -> BaseAdapter:
        """Instantiate the adapter registered for one explicit framework name."""

        normalized_framework_name = _normalized_framework_name(framework_name)
        adapter_type = self._adapter_types.get(normalized_framework_name)
        if adapter_type is None:
            self._ensure_defaults_registered()
            adapter_type = self._adapter_type_for_framework(normalized_framework_name)
        adapter = adapter_type()
        logger.debug(
            "Using explicit adapter %s for framework=%r",
            type(adapter).__name__,
            normalized_framework_name,
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
            return _normalized_framework_name(self.detect_adapter_type(circuit).framework_name)
        except UnsupportedFrameworkError:
            return None

    def detect_framework_name_from_registered(
        self,
        circuit: object,
        *,
        exclude_framework: str | None = None,
    ) -> str | None:
        """Return a detected framework using only the currently registered adapters."""

        normalized_excluded_framework = (
            _normalized_framework_name(exclude_framework) if exclude_framework is not None else None
        )
        for framework_name, adapter_type in self._adapter_types.items():
            if framework_name == normalized_excluded_framework:
                continue
            if adapter_type.can_handle(circuit):
                return framework_name
        return None

    def available_frameworks(self) -> tuple[str, ...]:
        """Return the registered framework names in registration order."""

        self._ensure_defaults_registered()
        return tuple(self._adapter_types)

    def unregister(self, framework_name: str, *, missing_ok: bool = False) -> None:
        """Remove one registered framework name from the registry."""

        self._ensure_defaults_registered()
        normalized_framework_name = _normalized_framework_name(framework_name)
        if normalized_framework_name not in self._adapter_types:
            if missing_ok:
                return
            raise ValueError(f"framework {normalized_framework_name!r} is not registered")
        self._adapter_types.pop(normalized_framework_name)
        logger.debug("Unregistered adapter for framework=%r", normalized_framework_name)

    def _adapter_type_for_framework(self, framework_name: str) -> type[BaseAdapter]:
        normalized_framework_name = _normalized_framework_name(framework_name)
        try:
            return self._adapter_types[normalized_framework_name]
        except KeyError as exc:
            available = ", ".join(sorted(self.available_frameworks()))
            raise UnsupportedFrameworkError(
                f"unsupported framework '{normalized_framework_name}'. Available adapters: {available}"
            ) from exc

    def _ensure_defaults_registered(self) -> None:
        if self._defaults_registered:
            return
        for adapter_type in _default_adapter_types():
            framework_name = _normalized_framework_name(adapter_type.framework_name)
            if framework_name in self._adapter_types:
                continue
            self._adapter_types[framework_name] = adapter_type
        self._defaults_registered = True

    @staticmethod
    def _validate_adapter_type(adapter_type: type[BaseAdapter]) -> type[BaseAdapter]:
        if not isinstance(adapter_type, type) or not issubclass(adapter_type, BaseAdapter):
            raise TypeError("adapter_type must be a BaseAdapter subclass")
        framework_name = getattr(adapter_type, "framework_name", None)
        if not isinstance(framework_name, str) or not framework_name.strip():
            raise ValueError("framework_name must be a non-empty string")
        return adapter_type


def _default_adapter_types() -> tuple[type[BaseAdapter], ...]:
    from .cirq_adapter import CirqAdapter
    from .cudaq_adapter import CudaqAdapter
    from .ir_adapter import IRAdapter
    from .myqlm_adapter import MyQLMAdapter
    from .pennylane_adapter import PennyLaneAdapter
    from .qiskit_adapter import QiskitAdapter

    return (IRAdapter, QiskitAdapter, CirqAdapter, PennyLaneAdapter, MyQLMAdapter, CudaqAdapter)


registry = AdapterRegistry()


def register_adapter(adapter_type: type[BaseAdapter], *, replace: bool = False) -> None:
    """Register one third-party adapter on the global registry."""

    registry.register(adapter_type, replace=replace)


def unregister_adapter(framework_name: str, *, missing_ok: bool = False) -> None:
    """Remove one framework name from the global registry."""

    registry.unregister(framework_name, missing_ok=missing_ok)


def available_frameworks() -> tuple[str, ...]:
    """Return the registered framework names from the global registry."""

    return registry.available_frameworks()


def detect_framework_name(circuit: object) -> str | None:
    """Return the detected framework name from the global registry."""

    return registry.detect_framework_name(circuit)


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

    detected_framework = registry.detect_framework_name_from_registered(
        circuit,
        exclude_framework=framework,
    )
    if detected_framework is not None:
        raise UnsupportedFrameworkError(
            f"requested framework '{framework}' does not match object of type {type(circuit)!r}; "
            f"autodetected '{detected_framework}'"
        )
    raise UnsupportedFrameworkError(
        f"requested framework '{framework}' does not match object of type {type(circuit)!r}"
    )


def _normalized_framework_name(framework_name: str) -> str:
    normalized_framework_name = framework_name.strip()
    if not normalized_framework_name:
        raise ValueError("framework_name must be a non-empty string")
    return normalized_framework_name
