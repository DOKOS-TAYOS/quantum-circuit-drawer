from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters.pennylane_adapter import PennyLaneAdapter
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind
from quantum_circuit_drawer.ir.semantic import SemanticCircuitIR
from tests.support import (
    OperationSignature,
    assert_classical_wire_bundles,
    assert_operation_signatures,
    assert_quantum_wire_labels,
)


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
        has_decomposition: bool = False,
        decomposition: tuple[object, ...] = (),
    ) -> None:
        self.name = name
        self.wires = wires
        self.parameters = parameters
        self.control_wires = control_wires
        self.target_wires = target_wires
        self.has_decomposition = has_decomposition
        self._decomposition = decomposition

    def decomposition(self) -> tuple[object, ...]:
        return self._decomposition


class FakeMidMeasureOperation(FakeOperation):
    def __init__(self, *, wires: tuple[object, ...], measurement_id: str) -> None:
        super().__init__(name="MidMeasureMP", wires=wires)
        self.id = measurement_id


class FakeMeasurement:
    def __init__(self, wires: tuple[object, ...], *, obs: object | None = None) -> None:
        self.wires = wires
        self.obs = obs
        self.mv = None


class SampleMP(FakeMeasurement):
    pass


class ProbabilityMP(FakeMeasurement):
    pass


class ExpectationMP(FakeMeasurement):
    pass


class StateMP(FakeMeasurement):
    pass


class FakeObservable:
    def __init__(
        self,
        *,
        name: str,
        wires: tuple[object, ...],
        operands: tuple[FakeObservable, ...] = (),
    ) -> None:
        self.name = name
        self.wires = wires
        self.operands = operands


class FakeMeasurementValue:
    def __init__(
        self,
        *,
        measurements: tuple[object, ...],
        branches: dict[tuple[int, ...], bool],
    ) -> None:
        self.measurements = measurements
        self.branches = branches


class FakeConditionalOperation:
    def __init__(self, *, base: FakeOperation, meas_val: FakeMeasurementValue) -> None:
        self.base = base
        self.meas_val = meas_val
        self.name = base.name
        self.wires = base.wires
        self.parameters = base.parameters


class FakeTapeWrapper:
    def __init__(self, tape: FakeQuantumTape) -> None:
        self.qtape = tape


class FakeQNodeLikeWrapper:
    def __init__(self, tape: FakeQuantumTape) -> None:
        self._tape = tape

    @property
    def qtape(self) -> object:
        raise AssertionError("qtape property should not be touched when _tape is already built")

    @property
    def tape(self) -> object:
        raise AssertionError("tape property should not be touched when _tape is already built")

    def construct(self, *args: object, **kwargs: object) -> object:
        raise AssertionError("construct() must not be called implicitly")


def install_fake_pennylane(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_module = ModuleType("pennylane")
    fake_module.tape = SimpleNamespace(
        QuantumTape=FakeQuantumTape,
        QuantumScript=FakeQuantumTape,
    )
    monkeypatch.setitem(sys.modules, "pennylane", fake_module)


def build_basic_fake_tape() -> FakeQuantumTape:
    return FakeQuantumTape(
        wires=(0, 1),
        operations=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(
                name="CNOT",
                wires=(0, 1),
                control_wires=(0,),
                target_wires=(1,),
            ),
        ),
        measurements=(SampleMP((1,)),),
    )


def test_pennylane_adapter_contract_converts_basic_stubbed_tape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(build_basic_fake_tape()))

    assert ir.metadata["framework"] == "pennylane"
    assert_quantum_wire_labels(ir, ["0", "1"])
    assert_classical_wire_bundles(ir, [])
    assert_operation_signatures(
        ir,
        [
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.H,
                "H",
                (),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.CONTROLLED_GATE,
                CanonicalGateFamily.X,
                "X",
                (),
                ("q1",),
                ("q0",),
            ),
            OperationSignature(
                OperationKind.GATE,
                CanonicalGateFamily.CUSTOM,
                "SAMPLE",
                (),
                ("q1",),
            ),
        ],
    )


def test_pennylane_adapter_contract_uses_prebuilt_private_tape_without_touching_properties(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    wrapper = FakeQNodeLikeWrapper(build_basic_fake_tape())

    assert PennyLaneAdapter.can_handle(wrapper) is True

    ir = PennyLaneAdapter().to_ir(wrapper)

    assert ir.metadata["framework"] == "pennylane"
    assert [operation.name for layer in ir.layers for operation in layer.operations] == [
        "H",
        "X",
        "SAMPLE",
    ]


def test_pennylane_adapter_contract_converts_stubbed_mid_measure_and_conditional_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    measured_bit = FakeMidMeasureOperation(wires=(0,), measurement_id="m0")
    conditional_x = FakeConditionalOperation(
        base=FakeOperation(name="PauliX", wires=(1,)),
        meas_val=FakeMeasurementValue(
            measurements=(measured_bit,),
            branches={(1,): True},
        ),
    )
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(measured_bit, conditional_x),
        measurements=(),
    )

    ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.kind for operation in operations] == [
        OperationKind.MEASUREMENT,
        OperationKind.GATE,
    ]
    assert operations[1].name == "X"
    assert operations[1].classical_conditions[0].wire_ids == ("c0",)
    assert operations[1].classical_conditions[0].expression == "if c[0]=1"


def test_pennylane_adapter_contract_expands_stubbed_composite_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    composite = FakeOperation(
        name="QFT",
        wires=(0, 1),
        has_decomposition=True,
        decomposition=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(
                name="CNOT",
                wires=(0, 1),
                control_wires=(0,),
                target_wires=(1,),
            ),
        ),
    )
    tape = FakeQuantumTape(wires=(0, 1), operations=(composite,), measurements=())

    compact_ir = PennyLaneAdapter().to_ir(FakeTapeWrapper(tape))
    expanded_ir = PennyLaneAdapter().to_ir(
        FakeTapeWrapper(tape),
        options={"composite_mode": "expand"},
    )

    compact_operations = [
        operation.name for layer in compact_ir.layers for operation in layer.operations
    ]
    expanded_operations = [
        operation.name for layer in expanded_ir.layers for operation in layer.operations
    ]

    assert compact_operations == ["QFT"]
    assert expanded_operations == ["H", "X"]


def test_pennylane_adapter_contract_exposes_semantic_conditional_and_decomposition_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    measured_bit = FakeMidMeasureOperation(wires=(0,), measurement_id="m0")
    conditional_x = FakeConditionalOperation(
        base=FakeOperation(name="PauliX", wires=(1,)),
        meas_val=FakeMeasurementValue(
            measurements=(measured_bit,),
            branches={(1,): True},
        ),
    )
    composite = FakeOperation(
        name="QFT",
        wires=(0, 1),
        has_decomposition=True,
        decomposition=(
            FakeOperation(name="Hadamard", wires=(0,)),
            FakeOperation(
                name="CNOT",
                wires=(0, 1),
                control_wires=(0,),
                target_wires=(1,),
            ),
        ),
    )
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(measured_bit, conditional_x, composite),
        measurements=(),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(
        FakeTapeWrapper(tape),
        options={"composite_mode": "expand", "explicit_matrices": False},
    )

    assert isinstance(semantic_ir, SemanticCircuitIR)
    assert semantic_ir.layers[1].operations[0].provenance.framework == "pennylane"
    assert semantic_ir.layers[1].operations[0].hover_details == ("conditional on: if c[0]=1",)
    assert semantic_ir.layers[2].operations[0].provenance.decomposition_origin == "QFT"


def test_pennylane_adapter_contract_keeps_terminal_outputs_as_gate_like_semantic_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_pennylane(monkeypatch)
    tape = FakeQuantumTape(
        wires=(0, 1),
        operations=(),
        measurements=(
            ExpectationMP((0,), obs=FakeObservable(name="PauliZ", wires=(0,))),
            ProbabilityMP((0, 1)),
            StateMP(()),
        ),
    )

    semantic_ir = PennyLaneAdapter().to_semantic_ir(FakeTapeWrapper(tape))
    operations = [operation for layer in semantic_ir.layers for operation in layer.operations]

    assert semantic_ir.classical_wires == ()
    assert [operation.name for operation in operations] == ["EXPVAL", "PROBS", "STATE"]
    assert all(operation.kind is OperationKind.GATE for operation in operations)
    assert operations[0].metadata["pennylane_terminal_kind"] == "expval"
    assert operations[0].metadata["pennylane_observable_label"] == "PauliZ"
    assert operations[1].target_wires == ("q0", "q1")
    assert operations[2].target_wires == ("q0", "q1")
