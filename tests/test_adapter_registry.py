from __future__ import annotations

import importlib

import pytest

from quantum_circuit_drawer.adapters.base import BaseAdapter
from quantum_circuit_drawer.adapters.registry import AdapterRegistry, get_adapter
from quantum_circuit_drawer.exceptions import UnsupportedFrameworkError
from quantum_circuit_drawer.ir.circuit import CircuitIR


class _Marker:
    pass


class _FirstAdapter(BaseAdapter):
    framework_name = "first"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, str)

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        return CircuitIR(quantum_wires=())


class _SecondAdapter(BaseAdapter):
    framework_name = "second"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, _Marker)

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        return CircuitIR(quantum_wires=())


class _FallbackAdapter(BaseAdapter):
    framework_name = "fallback"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return isinstance(circuit, _Marker)

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        return CircuitIR(quantum_wires=())


class _RequestedFrameworkAdapter(BaseAdapter):
    framework_name = "qiskit"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        return False

    def to_ir(self, circuit: object, options: dict[str, object] | None = None) -> CircuitIR:
        return CircuitIR(quantum_wires=())


def test_adapter_registry_detects_using_registration_order() -> None:
    registry = AdapterRegistry()
    registry.register(_SecondAdapter)
    registry.register(_FallbackAdapter)

    adapter = registry.detect(_Marker())

    assert isinstance(adapter, _SecondAdapter)


def test_adapter_registry_lists_default_frameworks() -> None:
    registry = AdapterRegistry()

    assert registry.available_frameworks() == (
        "ir",
        "qiskit",
        "cirq",
        "pennylane",
        "myqlm",
        "cudaq",
    )


def test_get_adapter_reports_detected_framework_on_explicit_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    registry.register(_FirstAdapter)
    registry.register(_SecondAdapter)
    monkeypatch.setattr(registry_module, "registry", registry)

    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"requested framework 'first'.*autodetected 'second'",
    ):
        get_adapter(_Marker(), framework="first")


def test_get_adapter_lists_available_frameworks_for_unknown_names() -> None:
    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"unsupported framework 'bogus'.*cirq.*cudaq.*ir.*myqlm.*pennylane.*qiskit",
    ):
        get_adapter(object(), framework="bogus")


def test_get_adapter_reports_requested_framework_when_object_is_not_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_module = importlib.import_module("quantum_circuit_drawer.adapters.registry")
    registry = AdapterRegistry()
    registry.register(_RequestedFrameworkAdapter, replace=True)
    monkeypatch.setattr(registry_module, "registry", registry)

    with pytest.raises(
        UnsupportedFrameworkError,
        match=r"requested framework 'qiskit' does not match object of type",
    ):
        get_adapter(object(), framework="qiskit")
