from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType

import pytest

from quantum_circuit_drawer.adapters.cirq_adapter import CirqAdapter
from quantum_circuit_drawer.ir.operations import OperationKind


class FakeQubit:
    def __init__(self, label: str) -> None:
        self.label = label

    def __str__(self) -> str:
        return self.label


class FakeOperation:
    def __init__(self, gate: object, qubits: tuple[FakeQubit, ...]) -> None:
        self.gate = gate
        self.qubits = qubits


class FakeMoment:
    def __init__(self, *operations: FakeOperation) -> None:
        self.operations = operations


class FakeCircuit:
    def __init__(self, *moments: FakeMoment) -> None:
        self._moments = moments

    def all_qubits(self) -> set[FakeQubit]:
        return {
            qubit
            for moment in self._moments
            for operation in moment.operations
            for qubit in operation.qubits
        }

    def __iter__(self) -> Iterator[FakeMoment]:
        return iter(self._moments)


class MeasurementGate:
    def __init__(self, key: str) -> None:
        self.key = key


class HPowGate:
    exponent = 1


class CNotPowGate:
    exponent = 1


class XPowGate:
    exponent = 1


class FakeClassicalControl:
    def __init__(self, key: str) -> None:
        self.key = key


class FakeClassicallyControlledOperation:
    def __init__(self, base_operation: FakeOperation, key: str) -> None:
        self._base_operation = base_operation
        self.qubits = base_operation.qubits
        self.classical_controls = (FakeClassicalControl(key),)

    def without_classical_controls(self) -> FakeOperation:
        return self._base_operation


def install_fake_cirq(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("cirq")
    fake_module.Circuit = FakeCircuit
    fake_module.ClassicallyControlledOperation = FakeClassicallyControlledOperation
    fake_module.CircuitOperation = type("CircuitOperation", (), {})
    fake_module.ControlledOperation = type("ControlledOperation", (), {})
    fake_module.unitary = lambda operation, default=None: default
    monkeypatch.setitem(sys.modules, "cirq", fake_module)


def test_cirq_adapter_contract_converts_basic_stubbed_circuit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    circuit = FakeCircuit(
        FakeMoment(FakeOperation(HPowGate(), (q0,))),
        FakeMoment(FakeOperation(CNotPowGate(), (q0, q1))),
        FakeMoment(FakeOperation(MeasurementGate("m"), (q1,))),
    )

    ir = CirqAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [wire.label for wire in ir.quantum_wires] == ["q(0)", "q(1)"]
    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].metadata["bundle_size"] == 1
    assert [operation.name for operation in operations] == ["H", "X", "M"]
    assert [operation.kind for operation in operations] == [
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.MEASUREMENT,
    ]


def test_cirq_adapter_contract_converts_stubbed_classical_controls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    measured = FakeOperation(MeasurementGate("m"), (q0,))
    controlled_x = FakeClassicallyControlledOperation(
        FakeOperation(XPowGate(), (q1,)),
        key="m",
    )
    circuit = FakeCircuit(
        FakeMoment(measured),
        FakeMoment(controlled_x),
    )

    ir = CirqAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[-1].name == "X"
    assert operations[-1].classical_conditions[0].wire_ids == ("c0",)
    assert operations[-1].classical_conditions[0].expression == "if c[0]=1"
