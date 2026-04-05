from __future__ import annotations

import runpy
import sys
from collections.abc import Callable
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from quantum_circuit_drawer.adapters.pennylane_adapter import PennyLaneAdapter
from quantum_circuit_drawer.exceptions import UnsupportedFrameworkError
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind


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


def _pennylane_available() -> bool:
    return find_spec("pennylane") is not None


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
    assert "H" in names
    assert "X" in names


def test_pennylane_adapter_maps_additional_canonical_gate_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(
            FakeOperation(name="PhaseShift", wires=(0,), parameters=(0.125,)),
            FakeOperation(name="Adjoint(S)", wires=(0,)),
            FakeOperation(name="Adjoint(T)", wires=(1,)),
            FakeOperation(name="SX", wires=(1,)),
            FakeOperation(name="U3", wires=(0,), parameters=(0.1, 0.2, 0.3)),
            FakeOperation(name="ISWAP", wires=(0, 1)),
        ),
        measurements=(),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    signatures = [
        (operation.kind, operation.canonical_family, operation.name, tuple(operation.parameters))
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.P, "P", (0.125,)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.SDG, "Sdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.TDG, "Tdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.SX, "SX", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.U, "U", (0.1, 0.2, 0.3)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.ISWAP, "iSWAP", ()) in signatures


def test_pennylane_adapter_rejects_non_tape_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_pennylane(monkeypatch)

    with pytest.raises(UnsupportedFrameworkError, match="PennyLane support in v0.1"):
        PennyLaneAdapter().to_ir(object())


def test_pennylane_adapter_supports_additional_common_operations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1, 2),
        operations=(
            FakeOperation(name="Identity", wires=(0,)),
            FakeOperation(name="Reset", wires=(1,)),
            FakeOperation(name="Delay", wires=(2,), parameters=(12,)),
            FakeOperation(name="ECR", wires=(0, 2)),
            FakeOperation(name="RXX", wires=(0, 1), parameters=(0.5,)),
            FakeOperation(name="RYY", wires=(1, 2), parameters=(0.6,)),
            FakeOperation(name="RZZ", wires=(0, 2), parameters=(0.7,)),
            FakeOperation(name="RZX", wires=(0, 1), parameters=(0.8,)),
            FakeOperation(name="FSim", wires=(1, 2), parameters=(0.2, 0.3)),
            FakeOperation(
                name="RZZ",
                wires=(0, 1, 2),
                parameters=(0.125,),
                control_wires=(0,),
                target_wires=(1, 2),
            ),
        ),
        measurements=(),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    signatures = [
        (
            operation.kind,
            operation.canonical_family,
            operation.name,
            tuple(operation.parameters),
            tuple(operation.target_wires),
            tuple(operation.control_wires),
        )
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.CUSTOM, "I", (), ("q0",), ()) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "RESET",
        (),
        ("q1",),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "DELAY",
        (12,),
        ("q2",),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "ECR",
        (),
        ("q0", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "RXX",
        (0.5,),
        ("q0", "q1"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "RYY",
        (0.6,),
        ("q1", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "RZZ",
        (0.7,),
        ("q0", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "RZX",
        (0.8,),
        ("q0", "q1"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.CUSTOM,
        "FSIM",
        (0.2, 0.3),
        ("q1", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.CUSTOM,
        "RZZ",
        (0.125,),
        ("q1", "q2"),
        ("q0",),
    ) in signatures


@pytest.mark.parametrize(
    "example_name",
    [
        "pennylane_example.py",
        "pennylane_wide_example.py",
        "pennylane_deep_example.py",
        "pennylane_grover_example.py",
        "pennylane_qaoa_example.py",
    ],
)
@pytest.mark.skipif(not _pennylane_available(), reason="PennyLane example tests require pennylane")
def test_pennylane_examples_build_valid_tapes(example_name: str) -> None:
    example_path = Path(__file__).resolve().parents[1] / "examples" / example_name
    namespace = runpy.run_path(str(example_path))
    build_tape = cast(Callable[[], object], namespace["build_tape"])

    tape = build_tape()

    assert hasattr(tape, "operations")
    assert hasattr(tape, "measurements")
