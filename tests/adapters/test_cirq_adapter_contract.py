from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace

import pytest

from quantum_circuit_drawer.adapters.cirq_adapter import CirqAdapter
from quantum_circuit_drawer.ir.operations import OperationKind
from quantum_circuit_drawer.ir.semantic import SemanticCircuitIR


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


class FakeFrozenCircuit:
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
    def __init__(self, key: str, *, index: int | None = None, value: int | None = None) -> None:
        self.key = key
        self.index = index
        self.value = value

    def __repr__(self) -> str:
        return f"FakeClassicalControl(key={self.key!r}, index={self.index!r}, value={self.value!r})"


class FakeControlledOperation:
    def __init__(
        self,
        *,
        controls: tuple[FakeQubit, ...],
        sub_operation: FakeOperation,
        control_values: tuple[tuple[int, ...], ...],
        tags: tuple[object, ...] = (),
    ) -> None:
        self.controls = controls
        self.sub_operation = sub_operation
        self.control_values = control_values
        self.qubits = (*controls, *sub_operation.qubits)
        self.tags = tags


class FakeClassicallyControlledOperation:
    def __init__(
        self,
        base_operation: FakeOperation,
        key: str,
        *,
        index: int | None = None,
        value: int | None = None,
        controls: tuple[FakeClassicalControl, ...] | None = None,
        tags: tuple[object, ...] = (),
    ) -> None:
        self._base_operation = base_operation
        self.qubits = base_operation.qubits
        self.classical_controls = controls or (FakeClassicalControl(key, index=index, value=value),)
        self.tags = tags

    def without_classical_controls(self) -> FakeOperation:
        return self._base_operation


class FakeTaggedOperation:
    def __init__(self, operation: FakeOperation, *tags: object) -> None:
        self.sub_operation = operation
        self.gate = getattr(operation, "gate", None)
        self.qubits = operation.qubits
        self.tags = tags

    @property
    def untagged(self) -> FakeOperation:
        return self.sub_operation


class CircuitOperation:
    def __init__(
        self,
        mapped_circuit_value: FakeCircuit,
        qubits: tuple[FakeQubit, ...],
    ) -> None:
        self._mapped_circuit_value = mapped_circuit_value
        self.qubits = qubits

    def mapped_circuit(self) -> FakeCircuit:
        return self._mapped_circuit_value


def install_fake_cirq(
    monkeypatch: pytest.MonkeyPatch,
    *,
    unitary: object | None = None,
) -> None:
    fake_module = ModuleType("cirq")
    fake_module.Circuit = FakeCircuit
    fake_module.FrozenCircuit = FakeFrozenCircuit
    fake_module.ClassicallyControlledOperation = FakeClassicallyControlledOperation
    fake_module.CircuitOperation = CircuitOperation
    fake_module.ControlledOperation = FakeControlledOperation
    fake_module.unitary = unitary or (lambda operation, default=None: default)
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


def test_cirq_adapter_contract_accepts_stubbed_frozen_circuit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    circuit = FakeFrozenCircuit(
        FakeMoment(FakeOperation(HPowGate(), (q0,))),
        FakeMoment(FakeOperation(CNotPowGate(), (q0, q1))),
    )

    assert CirqAdapter.can_handle(circuit) is True

    ir = CirqAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [wire.label for wire in ir.quantum_wires] == ["q(0)", "q(1)"]
    assert [operation.name for operation in operations] == ["H", "X"]


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


def test_cirq_adapter_contract_preserves_stubbed_control_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    controlled_x = FakeControlledOperation(
        controls=(q0,),
        sub_operation=FakeOperation(XPowGate(), (q1,)),
        control_values=((0,),),
    )
    circuit = FakeCircuit(FakeMoment(controlled_x))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.kind is OperationKind.CONTROLLED_GATE
    assert operation.control_values == ((0,),)


def test_cirq_adapter_contract_preserves_stubbed_key_condition_index_and_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    measured = FakeOperation(MeasurementGate("m"), (q0,))
    controlled_x = FakeClassicallyControlledOperation(
        FakeOperation(XPowGate(), (q1,)),
        key="m",
        index=0,
        value=0,
    )
    circuit = FakeCircuit(FakeMoment(measured), FakeMoment(controlled_x))

    ir = CirqAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[-1].classical_conditions[0].expression == "if c[0]=0"


def test_cirq_adapter_contract_treats_negative_key_condition_index_as_whole_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    measured = FakeOperation(MeasurementGate("m"), (q0,))
    controlled_x = FakeClassicallyControlledOperation(
        FakeOperation(XPowGate(), (q1,)),
        key="m",
        index=-1,
    )
    circuit = FakeCircuit(FakeMoment(measured), FakeMoment(controlled_x))

    ir = CirqAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[-1].classical_conditions[0].wire_ids == ("c0",)
    assert operations[-1].classical_conditions[0].expression == "if c[0]=1"


def test_cirq_adapter_contract_falls_back_to_native_hover_when_any_classical_control_is_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    measured = FakeOperation(MeasurementGate("m"), (q0,))
    controlled_x = FakeClassicallyControlledOperation(
        FakeOperation(XPowGate(), (q1,)),
        key="m",
        controls=(
            FakeClassicalControl("m"),
            FakeClassicalControl("missing", value=0),
        ),
    )
    circuit = FakeCircuit(FakeMoment(measured), FakeMoment(controlled_x))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[-1].operations[0]

    assert operation.classical_conditions == ()
    assert operation.hover_details == (
        "group: moment[1]",
        "conditional on: FakeClassicalControl(key='m', index=None, value=None)",
        "conditional on: FakeClassicalControl(key='missing', index=None, value=0)",
    )


def test_cirq_adapter_contract_falls_back_to_native_hover_for_unsupported_classical_condition_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    measured = FakeOperation(MeasurementGate("m"), (q0,))
    controlled_x = FakeClassicallyControlledOperation(
        FakeOperation(XPowGate(), (q1,)),
        key="m",
        index=2,
        value=0,
    )
    circuit = FakeCircuit(FakeMoment(measured), FakeMoment(controlled_x))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[-1].operations[0]

    assert operation.classical_conditions == ()
    assert operation.hover_details == (
        "group: moment[1]",
        "conditional on: FakeClassicalControl(key='m', index=2, value=0)",
    )


def test_cirq_adapter_contract_keeps_nontrivial_control_values_in_hover(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    q2 = FakeQubit("q(2)")
    controlled_x = FakeControlledOperation(
        controls=(q0, q2),
        sub_operation=FakeOperation(XPowGate(), (q1,)),
        control_values=((0, 1), (1,)),
    )
    circuit = FakeCircuit(FakeMoment(controlled_x))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.control_values == ((0, 1), (1,))
    assert operation.hover_details == (
        "group: moment[0]",
        "control values: (0, 1), (1)",
    )


def test_cirq_adapter_contract_keeps_open_control_values_aligned_with_control_wires(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    q2 = FakeQubit("q(2)")
    controlled_x = FakeControlledOperation(
        controls=(q0, q1),
        sub_operation=FakeOperation(XPowGate(), (q2,)),
        control_values=((0,), (1,)),
    )
    circuit = FakeCircuit(FakeMoment(controlled_x))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.control_wires == ("q0", "q1")
    assert operation.control_values == ((0,), (1,))


def test_cirq_adapter_contract_prefers_iterable_control_values_over_expanded_combinations() -> None:
    class _FakeProductOfSums:
        def __iter__(self) -> object:
            return iter(((0,), (1,)))

        def expand(self) -> tuple[tuple[int, ...], ...]:
            return ((0, 1),)

    controlled_operation = SimpleNamespace(control_values=_FakeProductOfSums())

    assert CirqAdapter()._control_values_for_controlled_operation(controlled_operation) == (
        (0,),
        (1,),
    )


def test_cirq_adapter_contract_keeps_nontrivial_iterable_control_values_per_wire() -> None:
    class _FakeProductOfSums:
        def __iter__(self) -> object:
            return iter(((0, 1), (1,)))

        def expand(self) -> tuple[tuple[int, ...], ...]:
            return ((0, 1), (1, 1))

    controlled_operation = SimpleNamespace(control_values=_FakeProductOfSums())

    assert CirqAdapter()._control_values_for_controlled_operation(controlled_operation) == (
        (0, 1),
        (1,),
    )


def test_cirq_adapter_contract_preserves_tags_in_hover_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    tagged_operation = FakeTaggedOperation(FakeOperation(XPowGate(), (q0,)), "tag-a", "tag-b")
    circuit = FakeCircuit(FakeMoment(tagged_operation))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.hover_details == (
        "group: moment[0]",
        "tags: tag-a, tag-b",
    )
    assert operation.metadata["cirq_tags"] == ("tag-a", "tag-b")


def test_cirq_adapter_contract_preserves_tagged_controlled_operation_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    tagged_operation = FakeTaggedOperation(
        FakeControlledOperation(
            controls=(q0,),
            sub_operation=FakeOperation(XPowGate(), (q1,)),
            control_values=((0,),),
        ),
        "tag-a",
    )
    circuit = FakeCircuit(FakeMoment(tagged_operation))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.kind is OperationKind.CONTROLLED_GATE
    assert operation.control_wires == ("q0",)
    assert operation.target_wires == ("q1",)
    assert operation.metadata["cirq_tags"] == ("tag-a",)


def test_cirq_adapter_contract_keeps_stubbed_circuit_operation_compact_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    nested = FakeCircuit(
        FakeMoment(FakeOperation(HPowGate(), (q0,))),
        FakeMoment(FakeOperation(CNotPowGate(), (q0, q1))),
    )
    circuit = FakeCircuit(
        FakeMoment(CircuitOperation(nested, (q0, q1))),
    )

    ir = CirqAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["CircuitOperation"]


def test_cirq_adapter_contract_expands_stubbed_circuit_operation_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    nested = FakeCircuit(
        FakeMoment(FakeOperation(HPowGate(), (q0,))),
        FakeMoment(FakeOperation(CNotPowGate(), (q0, q1))),
    )
    circuit = FakeCircuit(
        FakeMoment(CircuitOperation(nested, (q0, q1))),
    )

    ir = CirqAdapter().to_ir(
        circuit,
        options={"composite_mode": "expand", "explicit_matrices": False},
    )
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["H", "X"]


def test_cirq_adapter_contract_expands_stubbed_circuit_operation_measurements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    nested = FakeCircuit(
        FakeMoment(FakeOperation(MeasurementGate("nested"), (q0,))),
    )
    circuit = FakeCircuit(
        FakeMoment(CircuitOperation(nested, (q0,))),
    )

    ir = CirqAdapter().to_ir(
        circuit,
        options={"composite_mode": "expand", "explicit_matrices": False},
    )
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(ir.classical_wires) == 1
    assert operations[0].kind is OperationKind.MEASUREMENT
    assert operations[0].metadata["classical_bit_label"] == "c[0]"


def test_cirq_adapter_contract_skips_matrix_lookup_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def exploding_unitary(operation: object, default: object | None = None) -> object:
        del operation, default
        raise AssertionError("unitary lookup should not run when explicit_matrices=False")

    install_fake_cirq(monkeypatch, unitary=exploding_unitary)
    q0 = FakeQubit("q(0)")
    circuit = FakeCircuit(FakeMoment(FakeOperation(HPowGate(), (q0,))))

    ir = CirqAdapter().to_ir(circuit, options={"explicit_matrices": False})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert "matrix" not in operations[0].metadata


def test_cirq_adapter_contract_exposes_semantic_moment_and_composite_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_cirq(monkeypatch)
    q0 = FakeQubit("q(0)")
    q1 = FakeQubit("q(1)")
    nested = FakeCircuit(
        FakeMoment(FakeOperation(HPowGate(), (q0,))),
        FakeMoment(FakeOperation(CNotPowGate(), (q0, q1))),
    )
    circuit = FakeCircuit(FakeMoment(CircuitOperation(nested, (q0, q1))))

    semantic_ir = CirqAdapter().to_semantic_ir(
        circuit,
        options={"composite_mode": "expand", "explicit_matrices": False},
    )

    assert isinstance(semantic_ir, SemanticCircuitIR)
    assert len(semantic_ir.layers) == 2
    assert (
        semantic_ir.layers[0].metadata["native_group"] == "moment[0]/CircuitOperation[0]/moment[0]"
    )
    assert semantic_ir.layers[0].operations[0].provenance.framework == "cirq"
    assert semantic_ir.layers[0].operations[0].provenance.decomposition_origin == "CircuitOperation"
