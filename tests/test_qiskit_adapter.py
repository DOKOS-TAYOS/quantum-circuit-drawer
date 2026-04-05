from __future__ import annotations

import pytest

qiskit = pytest.importorskip("qiskit")

from quantum_circuit_drawer.adapters.qiskit_adapter import QiskitAdapter
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