from __future__ import annotations

import builtins

import pytest

from quantum_circuit_drawer.adapters.cirq_adapter import CirqAdapter
from quantum_circuit_drawer.adapters.ir_adapter import IRAdapter
from quantum_circuit_drawer.adapters.pennylane_adapter import PennyLaneAdapter
from quantum_circuit_drawer.adapters.qiskit_adapter import QiskitAdapter


@pytest.mark.parametrize(
    ("adapter_type", "module_name"),
    [
        (QiskitAdapter, "qiskit"),
        (CirqAdapter, "cirq"),
        (PennyLaneAdapter, "pennylane"),
    ],
)
def test_adapter_can_handle_returns_false_when_dependency_is_missing(
    adapter_type: type[QiskitAdapter] | type[CirqAdapter] | type[PennyLaneAdapter],
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == module_name or name.startswith(f"{module_name}."):
            raise ModuleNotFoundError(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert adapter_type.can_handle(object()) is False


@pytest.mark.parametrize(
    ("adapter_type", "module_name"),
    [
        (QiskitAdapter, "qiskit"),
        (CirqAdapter, "cirq"),
        (PennyLaneAdapter, "pennylane"),
    ],
)
def test_adapter_can_handle_does_not_swallow_unexpected_import_errors(
    adapter_type: type[QiskitAdapter] | type[CirqAdapter] | type[PennyLaneAdapter],
    module_name: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == module_name or name.startswith(f"{module_name}."):
            raise RuntimeError(f"boom: {module_name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match=f"boom: {module_name}"):
        adapter_type.can_handle(object())


def test_ir_adapter_raises_type_error_for_non_ir_objects() -> None:
    with pytest.raises(TypeError, match="CircuitIR"):
        IRAdapter().to_ir(object())
