from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters.pennylane_adapter import PennyLaneAdapter
from quantum_circuit_drawer.exceptions import UnsupportedFrameworkError
from quantum_circuit_drawer.ir.operations import OperationKind


class FakeQuantumTape:
    def __init__(
        self,
        *,
        wires: tuple[object, ...],
        operations: tuple[object, ...],
        measurements: tuple[object, ...],
    ) -> None:
        self.wires = wires
        self.operations = operations
        self.measurements = measurements


class FakeOperation:
    def __init__(
        self,
        *,
        name: str,
        wires: tuple[object, ...],
        parameters: tuple[object, ...] = (),
        control_wires: tuple[object, ...] = (),
        target_wires: tuple[object, ...] | None = None,
    ) -> None:
        self.name = name
        self.wires = wires
        self.parameters = parameters
        self.control_wires = control_wires
        self.target_wires = target_wires


class FakeMeasurement:
    def __init__(self, wires: tuple[object, ...]) -> None:
        self.wires = wires


class FakeTapeWrapper:
    def __init__(self, tape: FakeQuantumTape) -> None:
        self.qtape = tape


def install_fake_pennylane(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("pennylane")
    fake_module.tape = SimpleNamespace(QuantumTape=FakeQuantumTape, QuantumScript=FakeQuantumTape)
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)


def build_fake_tape() -> FakeQuantumTape:
    return FakeQuantumTape(
        wires=(0, 1),
        operations=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(name="CNOT", wires=(0, 1), control_wires=(0,), target_wires=(1,)),
        ),
        measurements=(FakeMeasurement((1,)),),
    )


def test_pennylane_adapter_converts_tape_like_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pennylane(monkeypatch)

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(build_fake_tape()))

    kinds = [operation.kind for layer in ir.layers for operation in layer.operations]
    names = [operation.name for layer in ir.layers for operation in layer.operations]

    assert ir.metadata["framework"] == "pennylane"
    assert [wire.label for wire in ir.quantum_wires] == ["0", "1"]
    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].metadata["bundle_size"] == 1
    assert OperationKind.GATE in kinds
    assert OperationKind.CONTROLLED_GATE in kinds
    assert OperationKind.MEASUREMENT in kinds
    assert "Hadamard" in names
    assert "CNOT" in names


def test_pennylane_adapter_rejects_non_tape_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pennylane(monkeypatch)

    with pytest.raises(UnsupportedFrameworkError, match="PennyLane support in v0.1"):
        PennyLaneAdapter().to_ir(object())
