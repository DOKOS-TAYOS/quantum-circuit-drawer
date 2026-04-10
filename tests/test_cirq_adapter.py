from __future__ import annotations

import pytest

cirq = pytest.importorskip("cirq")

from quantum_circuit_drawer.adapters.cirq_adapter import CirqAdapter
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind


def test_cirq_adapter_converts_common_operations() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(
        cirq.H(q0),
        cirq.CNOT(q0, q1),
        cirq.SWAP(q0, q1),
        cirq.measure(q1, key="m"),
    )

    ir = CirqAdapter().to_ir(circuit)

    names = [operation.name for layer in ir.layers for operation in layer.operations]
    kinds = [operation.kind for layer in ir.layers for operation in layer.operations]

    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].label == "c"
    assert ir.classical_wires[0].metadata["bundle_size"] == 1
    assert "H" in names
    assert "X" in names
    assert OperationKind.SWAP in kinds
    assert OperationKind.MEASUREMENT in kinds


def test_cirq_adapter_keeps_individual_classical_bit_labels() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(cirq.measure(q0, q1, key="m"))

    ir = CirqAdapter().to_ir(circuit)

    measurements = [operation for layer in ir.layers for operation in layer.operations]

    assert [measurement.metadata["classical_bit_label"] for measurement in measurements] == [
        "c[0]",
        "c[1]",
    ]


def test_cirq_adapter_maps_canonical_gate_families() -> None:
    q0, q1, q2 = cirq.LineQubit.range(3)
    circuit = cirq.Circuit(
        cirq.H(q0),
        cirq.rz(0.5)(q1),
        cirq.CNOT(q0, q1),
        cirq.CZ(q1, q2),
        cirq.X(q2).controlled_by(q0, q1),
        cirq.rz(0.25)(q2).controlled_by(q0),
    )

    ir = CirqAdapter().to_ir(circuit)
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


def test_cirq_adapter_maps_additional_canonical_gate_families() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(
        cirq.S(q0),
        cirq.Z(q1) ** -0.5,
        cirq.T(q0),
        cirq.Z(q1) ** -0.25,
        cirq.X(q0) ** 0.5,
        cirq.X(q1) ** -0.5,
        cirq.ISWAP(q0, q1),
    )

    ir = CirqAdapter().to_ir(circuit)
    signatures = [
        (operation.canonical_family, operation.name, tuple(operation.parameters))
        for layer in ir.layers
        for operation in layer.operations
    ]

    assert (CanonicalGateFamily.S, "S", ()) in signatures
    assert (CanonicalGateFamily.SDG, "Sdg", ()) in signatures
    assert (CanonicalGateFamily.T, "T", ()) in signatures
    assert (CanonicalGateFamily.TDG, "Tdg", ()) in signatures
    assert (CanonicalGateFamily.SX, "SX", ()) in signatures
    assert (CanonicalGateFamily.SXDG, "SXdg", ()) in signatures
    assert (CanonicalGateFamily.ISWAP, "iSWAP", ()) in signatures


def test_cirq_adapter_converts_classically_controlled_operations() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(cirq.measure(q0, key="m"), cirq.X(q1).with_classical_controls("m"))

    ir = CirqAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[-1].name == "X"
    assert operations[-1].classical_conditions[0].wire_ids == ("c0",)
    assert operations[-1].classical_conditions[0].expression == "if c[0]=1"


def test_cirq_adapter_keeps_circuit_operation_compact_by_default() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    subcircuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1))
    circuit = cirq.Circuit(cirq.CircuitOperation(subcircuit.freeze()))

    ir = CirqAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(operations) == 1
    assert operations[0].name == "CircuitOperation"
    assert operations[0].target_wires == ("q0", "q1")


def test_cirq_adapter_expands_circuit_operation_when_requested() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    subcircuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1))
    circuit = cirq.Circuit(cirq.CircuitOperation(subcircuit.freeze()))

    ir = CirqAdapter().to_ir(circuit, options={"composite_mode": "expand"})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert [operation.name for operation in operations] == ["H", "X"]


def test_cirq_adapter_expands_circuit_operation_with_measurement() -> None:
    q0 = cirq.LineQubit(0)
    subcircuit = cirq.FrozenCircuit(cirq.measure(q0, key="nested"))
    circuit = cirq.Circuit(cirq.CircuitOperation(subcircuit))

    ir = CirqAdapter().to_ir(circuit, options={"composite_mode": "expand"})
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert len(ir.classical_wires) == 1
    assert ir.classical_wires[0].metadata["bundle_size"] == 1
    assert [operation.kind for operation in operations] == [OperationKind.MEASUREMENT]
    assert operations[0].target_wires == ("q0",)
    assert operations[0].metadata["classical_bit_label"] == "c[0]"


def test_cirq_adapter_supports_additional_common_operations() -> None:
    q0, q1, q2, q3 = cirq.LineQubit.range(4)
    circuit = cirq.Circuit(
        cirq.I(q0),
        cirq.reset(q1),
        cirq.XXPowGate(exponent=0.25)(q0, q1),
        cirq.YYPowGate(exponent=0.5)(q1, q2),
        cirq.ZZPowGate(exponent=0.75)(q2, q3),
        cirq.FSimGate(theta=0.2, phi=0.3)(q0, q3),
        cirq.ZZPowGate(exponent=0.125)(q2, q3).controlled_by(q0),
    )

    ir = CirqAdapter().to_ir(circuit)
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
        CanonicalGateFamily.RXX,
        "RXX",
        (0.25,),
        ("q0", "q1"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RYY,
        "RYY",
        (0.5,),
        ("q1", "q2"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.RZZ,
        "RZZ",
        (0.75,),
        ("q2", "q3"),
        (),
    ) in signatures
    assert (
        OperationKind.GATE,
        CanonicalGateFamily.FSIM,
        "FSIM",
        (0.2, 0.3),
        ("q0", "q3"),
        (),
    ) in signatures
    assert (
        OperationKind.CONTROLLED_GATE,
        CanonicalGateFamily.RZZ,
        "RZZ",
        (0.125,),
        ("q2", "q3"),
        ("q0",),
    ) in signatures
