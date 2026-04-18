from __future__ import annotations

import builtins
import sys
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters.cirq_adapter import CirqAdapter
from quantum_circuit_drawer.adapters.cudaq_adapter import CudaqAdapter
from quantum_circuit_drawer.adapters.ir_adapter import IRAdapter
from quantum_circuit_drawer.adapters.myqlm_adapter import MyQLMAdapter
from quantum_circuit_drawer.adapters.pennylane_adapter import PennyLaneAdapter
from quantum_circuit_drawer.adapters.qiskit_adapter import QiskitAdapter


@pytest.mark.parametrize(
    ("adapter_type", "module_name"),
    [
        (QiskitAdapter, "qiskit"),
        (CirqAdapter, "cirq"),
        (PennyLaneAdapter, "pennylane"),
        (MyQLMAdapter, "qat"),
        (CudaqAdapter, "cudaq"),
    ],
)
def test_adapter_can_handle_returns_false_when_dependency_is_missing(
    adapter_type: type[QiskitAdapter]
    | type[CirqAdapter]
    | type[PennyLaneAdapter]
    | type[MyQLMAdapter]
    | type[CudaqAdapter],
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
        (MyQLMAdapter, "qat"),
        (CudaqAdapter, "cudaq"),
    ],
)
def test_adapter_can_handle_does_not_swallow_unexpected_import_errors(
    adapter_type: type[QiskitAdapter]
    | type[CirqAdapter]
    | type[PennyLaneAdapter]
    | type[MyQLMAdapter]
    | type[CudaqAdapter],
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


def test_myqlm_adapter_can_handle_does_not_swallow_nested_import_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__
    fake_qat = ModuleType("qat")
    fake_qat.__path__ = []

    monkeypatch.setitem(sys.modules, "qat", fake_qat)

    def fake_import(
        name: str,
        globals: object | None = None,
        locals: object | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "qat":
            return fake_qat
        if name == "qat.core":
            raise RuntimeError("boom: qat.core")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError, match="boom: qat.core"):
        MyQLMAdapter.can_handle(object())


def test_pennylane_adapter_can_handle_rejects_invalid_wrapper_payloads(
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
        if name == "pennylane" or name.startswith("pennylane."):
            raise ModuleNotFoundError(name)
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert PennyLaneAdapter.can_handle(SimpleNamespace(tape=object())) is False


def test_qiskit_adapter_matrix_metadata_does_not_swallow_unexpected_errors() -> None:
    class _BrokenMatrixOperation:
        def to_matrix(self) -> object:
            raise RuntimeError("boom: qiskit matrix")

    with pytest.raises(RuntimeError, match="boom: qiskit matrix"):
        QiskitAdapter()._matrix_metadata(_BrokenMatrixOperation())


def test_qiskit_adapter_matrix_metadata_skips_framework_lookup_when_disabled() -> None:
    class _BrokenMatrixOperation:
        def to_matrix(self) -> object:
            raise RuntimeError("boom: qiskit matrix")

    assert QiskitAdapter()._matrix_metadata(_BrokenMatrixOperation(), explicit_matrices=False) == {}


def test_cirq_adapter_matrix_metadata_does_not_swallow_unexpected_errors() -> None:
    class _BrokenCirqModule:
        @staticmethod
        def unitary(operation: object, default: object | None = None) -> object:
            del operation, default
            raise RuntimeError("boom: cirq unitary")

    with pytest.raises(RuntimeError, match="boom: cirq unitary"):
        CirqAdapter()._matrix_metadata(cirq=_BrokenCirqModule(), operation=object())


def test_cirq_adapter_matrix_metadata_skips_framework_lookup_when_disabled() -> None:
    class _BrokenCirqModule:
        @staticmethod
        def unitary(operation: object, default: object | None = None) -> object:
            del operation, default
            raise RuntimeError("boom: cirq unitary")

    assert (
        CirqAdapter()._matrix_metadata(
            cirq=_BrokenCirqModule(),
            operation=object(),
            explicit_matrices=False,
        )
        == {}
    )


def test_pennylane_adapter_matrix_metadata_does_not_swallow_unexpected_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("pennylane")

    def fake_matrix(operation: object) -> object:
        del operation
        raise RuntimeError("boom: pennylane matrix")

    fake_module.matrix = fake_matrix
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)

    with pytest.raises(RuntimeError, match="boom: pennylane matrix"):
        PennyLaneAdapter()._matrix_metadata(object())


def test_pennylane_adapter_matrix_metadata_skips_framework_lookup_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType("pennylane")

    def fake_matrix(operation: object) -> object:
        del operation
        raise RuntimeError("boom: pennylane matrix")

    fake_module.matrix = fake_matrix
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)

    assert PennyLaneAdapter()._matrix_metadata(object(), explicit_matrices=False) == {}
