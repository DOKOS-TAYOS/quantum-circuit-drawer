from __future__ import annotations

from types import SimpleNamespace

import pytest

qiskit = pytest.importorskip("qiskit")

from quantum_circuit_drawer.adapters.qiskit_adapter import QiskitAdapter
from quantum_circuit_drawer.exceptions import UnsupportedOperationError
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind


def test_qiskit_adapter_converts_common_operations() -> None:
    circuit = qiskit.QuantumCircuit(2, 1)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.swap(0, 1)
    circuit.barrier()
    circuit.measure(1, 0)

    ir = QiskitAdapter().to_ir(circuit)

    names = [operation.name for layer in ir.layers for operation in layer.operations]
    kinds = [operation.kind for layer in ir.layers for operation in layer.operations]

    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].label == "c"
    assert ir.classical_wires[0].metadata["bundle_size"] == 1
    assert "H" in names
    assert "X" in names
    assert OperationKind.SWAP in kinds
    assert OperationKind.BARRIER in kinds
    assert OperationKind.MEASUREMENT in kinds


def test_qiskit_adapter_preserves_temporal_order_when_packing_layers() -> None:
    circuit = qiskit.QuantumCircuit(3, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cz(1, 2)
    circuit.swap(0, 2)
    circuit.barrier()
    circuit.measure(1, 0)
    circuit.measure(2, 1)

    ir = QiskitAdapter().to_ir(circuit)

    layer_kinds = [[operation.kind for operation in layer.operations] for layer in ir.layers]

    assert layer_kinds == [
        [OperationKind.GATE],
        [OperationKind.CONTROLLED_GATE],
        [OperationKind.CONTROLLED_GATE],
        [OperationKind.SWAP],
        [OperationKind.BARRIER],
        [OperationKind.MEASUREMENT],
        [OperationKind.MEASUREMENT],
    ]


def test_qiskit_adapter_groups_classical_bits_by_register() -> None:
    quantum = qiskit.QuantumRegister(3, "q")
    first = qiskit.ClassicalRegister(2, "alpha")
    second = qiskit.ClassicalRegister(3, "beta")
    circuit = qiskit.QuantumCircuit(quantum, first, second)
    circuit.measure(0, first[0])
    circuit.measure(1, second[1])

    ir = QiskitAdapter().to_ir(circuit)

    assert [(wire.label, wire.metadata["bundle_size"]) for wire in ir.classical_wires] == [
        ("alpha", 2),
        ("beta", 3),
    ]
    assert [
        operation.classical_target for layer in ir.layers for operation in layer.operations
    ] == [
        ir.classical_wires[0].id,
        ir.classical_wires[1].id,
    ]


def test_qiskit_adapter_keeps_individual_classical_bit_labels() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(2, "alpha")
    circuit = qiskit.QuantumCircuit(quantum, classical)
    circuit.measure(0, classical[0])
    circuit.measure(1, classical[1])

    ir = QiskitAdapter().to_ir(circuit)

    measurements = [operation for layer in ir.layers for operation in layer.operations]

    assert [measurement.metadata["classical_bit_label"] for measurement in measurements] == [
        "alpha[0]",
        "alpha[1]",
    ]


def test_qiskit_adapter_maps_canonical_gate_families() -> None:
    circuit = qiskit.QuantumCircuit(3)
    circuit.h(0)
    circuit.rz(0.5, 1)
    circuit.cx(0, 1)
    circuit.cz(1, 2)
    circuit.ccx(0, 1, 2)
    circuit.crz(0.25, 0, 2)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]
    signatures = [
        (operation.kind, operation.canonical_family, len(operation.control_wires), operation.name)
        for operation in operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.H, 0, "H") in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.RZ, 0, "RZ") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.X, 1, "X") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.Z, 1, "Z") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.X, 2, "X") in signatures
    assert (OperationKind.CONTROLLED_GATE, CanonicalGateFamily.RZ, 1, "RZ") in signatures


def test_qiskit_adapter_maps_additional_canonical_gate_families() -> None:
    circuit = qiskit.QuantumCircuit(2)
    circuit.sdg(0)
    circuit.tdg(1)
    circuit.sx(0)
    circuit.p(0.25, 1)
    circuit.u(0.1, 0.2, 0.3, 0)
    circuit.iswap(0, 1)

    ir = QiskitAdapter().to_ir(circuit)
    signatures = [
        (operation.kind, operation.canonical_family, operation.name, tuple(operation.parameters))
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (OperationKind.GATE, CanonicalGateFamily.SDG, "Sdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.TDG, "Tdg", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.SX, "SX", ()) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.P, "P", (0.25,)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.U, "U", (0.1, 0.2, 0.3)) in signatures
    assert (OperationKind.GATE, CanonicalGateFamily.ISWAP, "iSWAP", ()) in signatures


def test_qiskit_adapter_converts_bit_if_test_into_classically_conditioned_operation() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)):
        circuit.x(1)

    ir = QiskitAdapter().to_ir(circuit)
    conditioned_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert conditioned_operation.name == "X"
    assert conditioned_operation.classical_conditions[0].wire_ids == ("c0",)
    assert conditioned_operation.classical_conditions[0].expression == "if c[0]=1"


def test_qiskit_adapter_converts_register_if_test_into_classically_conditioned_operation() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(2, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical, 3)):
        circuit.z(1)

    ir = QiskitAdapter().to_ir(circuit)
    conditioned_operation = next(operation for layer in ir.layers for operation in layer.operations)

    assert conditioned_operation.name == "Z"
    assert conditioned_operation.classical_conditions[0].wire_ids == ("c0",)
    assert conditioned_operation.classical_conditions[0].expression == "if c=3"


def test_qiskit_adapter_expands_multi_operation_if_block() -> None:
    quantum = qiskit.QuantumRegister(2, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)):
        circuit.x(1)
        circuit.z(1)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["X", "Z"]
    assert [operation.classical_conditions[0].expression for operation in operations] == [
        "if c[0]=1",
        "if c[0]=1",
    ]


def test_qiskit_adapter_keeps_if_else_as_compact_composite() -> None:
    quantum = qiskit.QuantumRegister(1, "q")
    classical = qiskit.ClassicalRegister(1, "c")
    circuit = qiskit.QuantumCircuit(quantum, classical)

    with circuit.if_test((classical[0], 1)) as else_:
        circuit.x(0)
    with else_:
        circuit.z(0)

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].name == "IF/ELSE"


def test_qiskit_adapter_keeps_composite_instruction_compact_by_default() -> None:
    subcircuit = qiskit.QuantumCircuit(2, name="my_sub")
    subcircuit.h(0)
    subcircuit.cx(0, 1)

    circuit = qiskit.QuantumCircuit(2)
    circuit.append(subcircuit.to_instruction(), [0, 1])

    ir = QiskitAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].name == "my_sub"
    assert operations[0].target_wires == ("q0", "q1")


def test_qiskit_adapter_expands_composite_instruction_when_requested() -> None:
    subcircuit = qiskit.QuantumCircuit(2, name="my_sub")
    subcircuit.h(0)
    subcircuit.cx(0, 1)

    circuit = qiskit.QuantumCircuit(2)
    circuit.append(subcircuit.to_instruction(), [0, 1])

    ir = QiskitAdapter().to_ir(circuit, options={"composite_mode": "expand"})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["H", "X"]


def test_qiskit_adapter_supports_additional_common_operations() -> None:
    circuit = qiskit.QuantumCircuit(4)
    circuit.id(0)
    circuit.reset(1)
    circuit.delay(12, 2, unit="ns")
    circuit.cy(0, 1)
    circuit.ch(1, 2)
    circuit.cp(0.125, 0, 3)
    circuit.cu(0.1, 0.2, 0.3, 0.4, 1, 2)
    circuit.rxx(0.5, 0, 1)
    circuit.ryy(0.6, 1, 2)
    circuit.rzz(0.7, 2, 3)
    circuit.rzx(0.8, 0, 2)
    circuit.ecr(1, 3)
    circuit.cswap(0, 1, 2)

    ir = QiskitAdapter().to_ir(circuit)
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

    assert (OperationKind.GATE, CanonicalGateFamily.I, "I", (), ("q0",), ()) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RESET,
        "RESET",
        (),
        ("q1",),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.DELAY,
        "DELAY",
        (12,),
        ("q2",),
        (),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.Y,
        "Y",
        (),
        ("q1",),
        ("q0",),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.H,
        "H",
        (),
        ("q2",),
        ("q1",),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.P,
        "P",
        (0.125,),
        ("q3",),
        ("q0",),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.U,
        "U",
        (0.1, 0.2, 0.3, 0.4),
        ("q2",),
        ("q1",),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RXX,
        "RXX",
        (0.5,),
        ("q0", "q1"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RYY,
        "RYY",
        (0.6,),
        ("q1", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RZZ,
        "RZZ",
        (0.7,),
        ("q2", "q3"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RZX,
        "RZX",
        (0.8,),
        ("q0", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.ECR,
        "ECR",
        (),
        ("q1", "q3"),
        (),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.CUSTOM,
        "SWAP",
        (),
        ("q1", "q2"),
        ("q0",),
    ) in signatures


<<<<<<< ours
<<<<<<< ours
def test_qiskit_adapter_raises_for_measure_without_classical_target() -> None:
    class _MeasureOperation:
        name = "measure"
        params: tuple[object, ...] = ()

    qubit = object()
    adapter = QiskitAdapter()

    with pytest.raises(
        UnsupportedOperationError,
        match=r"instruction 'measure' has no classical target",
    ):
        adapter._convert_instruction(
            (_MeasureOperation(), (qubit,), ()),
            {qubit: "q0"},
            {},
            {},
            composite_mode="compact",
=======
=======
>>>>>>> theirs
def test_qiskit_adapter_raises_for_misaligned_if_else_true_block_qubits() -> None:
    outer_qubits = ("outer-q0",)
    outer_clbits = ("outer-c0",)
    operation = SimpleNamespace(
        blocks=(
            SimpleNamespace(qubits=("inner-q0", "inner-q1"), clbits=("inner-c0",), data=()),
        ),
        condition=("outer-c0", 1),
    )

    with pytest.raises(UnsupportedOperationError, match="if_else true_block qubit mapping mismatch"):
        QiskitAdapter()._convert_if_else(
            operation=operation,
            qubits=outer_qubits,
            clbits=outer_clbits,
            qubit_ids={"outer-q0": "q0"},
            classical_targets={"outer-c0": ("c0", "c[0]")},
            register_targets={},
            composite_mode="expand",
        )


def test_qiskit_adapter_raises_for_misaligned_if_else_true_block_clbits() -> None:
    outer_qubits = ("outer-q0",)
    outer_clbits = ("outer-c0",)
    operation = SimpleNamespace(
        blocks=(
            SimpleNamespace(qubits=("inner-q0",), clbits=("inner-c0", "inner-c1"), data=()),
        ),
        condition=("outer-c0", 1),
    )

    with pytest.raises(UnsupportedOperationError, match="if_else true_block clbit mapping mismatch"):
        QiskitAdapter()._convert_if_else(
            operation=operation,
            qubits=outer_qubits,
            clbits=outer_clbits,
            qubit_ids={"outer-q0": "q0"},
            classical_targets={"outer-c0": ("c0", "c[0]")},
            register_targets={},
            composite_mode="expand",
        )


def test_qiskit_adapter_raises_for_misaligned_composite_definition_qubits() -> None:
    operation = SimpleNamespace(
        definition=SimpleNamespace(
            qubits=("inner-q0", "inner-q1"),
            clbits=(),
            data=(),
        )
    )

    with pytest.raises(
        UnsupportedOperationError,
        match="composite definition qubit mapping mismatch",
    ):
        QiskitAdapter()._expand_definition(
            operation=operation,
            qubits=("outer-q0",),
            clbits=(),
            qubit_ids={"outer-q0": "q0"},
            classical_targets={},
            composite_mode="expand",
        )


def test_qiskit_adapter_raises_for_misaligned_composite_definition_clbits() -> None:
    operation = SimpleNamespace(
        definition=SimpleNamespace(
            qubits=("inner-q0",),
            clbits=("inner-c0", "inner-c1"),
            data=(),
        )
    )

    with pytest.raises(
        UnsupportedOperationError,
        match="composite definition clbit mapping mismatch",
    ):
        QiskitAdapter()._expand_definition(
            operation=operation,
            qubits=("outer-q0",),
            clbits=("outer-c0",),
            qubit_ids={"outer-q0": "q0"},
            classical_targets={"outer-c0": ("c0", "c[0]")},
            composite_mode="expand",
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
        )
