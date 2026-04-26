from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

pytestmark = [pytest.mark.optional, pytest.mark.integration]

if sys.platform.startswith("win"):
    pytest.skip("Cirq collection is not reliable on native Windows", allow_module_level=True)

cirq_circuits = pytest.importorskip("cirq.circuits")
cirq_devices = pytest.importorskip("cirq.devices")
cirq_ops = pytest.importorskip("cirq.ops")
cirq_value = pytest.importorskip("cirq.value")

cirq = SimpleNamespace(
    BitMaskKeyCondition=cirq_value.BitMaskKeyCondition,
    Circuit=cirq_circuits.Circuit,
    CircuitOperation=cirq_circuits.CircuitOperation,
    CNOT=cirq_ops.CNOT,
    CZ=cirq_ops.CZ,
    FSimGate=cirq_ops.FSimGate,
    FrozenCircuit=cirq_circuits.FrozenCircuit,
    H=cirq_ops.H,
    I=cirq_ops.I,
    ISWAP=cirq_ops.ISWAP,
    LineQubit=cirq_devices.LineQubit,
    MeasurementKey=cirq_value.MeasurementKey,
    Moment=cirq_circuits.Moment,
    S=cirq_ops.S,
    SWAP=cirq_ops.SWAP,
    T=cirq_ops.T,
    X=cirq_ops.X,
    XXPowGate=cirq_ops.XXPowGate,
    YYPowGate=cirq_ops.YYPowGate,
    Z=cirq_ops.Z,
    ZZPowGate=cirq_ops.ZZPowGate,
    measure=cirq_ops.measure,
    reset=cirq_ops.reset,
    rz=cirq_ops.rz,
)

from quantum_circuit_drawer.adapters.cirq_adapter import CirqAdapter
from quantum_circuit_drawer.ir.operations import CanonicalGateFamily, OperationKind
from tests.support import (
    OperationSignature,
    assert_classical_wire_bundles,
    assert_operation_signatures,
    assert_quantum_wire_labels,
    flatten_operations,
)


def test_cirq_adapter_matches_canonical_contract() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(
        cirq.H(q0),
        cirq.CNOT(q0, q1),
        cirq.measure(q1, key="m"),
    )

    ir = CirqAdapter().to_ir(circuit)
    measurement = flatten_operations(ir)[-1]

    assert ir.metadata["framework"] == "cirq"
    assert_quantum_wire_labels(ir, ["q(0)", "q(1)"])
    assert_classical_wire_bundles(ir, [("c", 1)])
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
                OperationKind.MEASUREMENT,
                CanonicalGateFamily.CUSTOM,
                "M",
                (),
                ("q1",),
            ),
        ],
    )
    assert measurement.classical_target == "c0"
    assert measurement.metadata["classical_bit_label"] == "c[0]"


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


def test_cirq_adapter_attaches_framework_matrices_when_available() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1))

    ir = CirqAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    h_matrix = np.asarray(operations[0].metadata["matrix"])
    cx_matrix = np.asarray(operations[1].metadata["matrix"])

    assert h_matrix.shape == (2, 2)
    assert cx_matrix.shape == (4, 4)


def test_cirq_adapter_converts_classically_controlled_operations() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(cirq.measure(q0, key="m"), cirq.X(q1).with_classical_controls("m"))

    ir = CirqAdapter().to_ir(circuit)
    operations = [operation for layer in ir.layers for operation in layer.operations]

    assert operations[-1].name == "X"
    assert operations[-1].classical_conditions[0].wire_ids == ("c0",)
    assert operations[-1].classical_conditions[0].expression == "if c[0]=1"


def test_cirq_adapter_falls_back_to_native_hover_for_non_normalizable_classical_controls() -> None:
    q0, q1 = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(
        cirq.measure(q0, q1, key="m"),
        cirq.X(q1).with_classical_controls(
            cirq.BitMaskKeyCondition(cirq.MeasurementKey("m"), 0b10)
        ),
    )

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[-1].operations[0]

    assert operation.classical_conditions == ()
    assert operation.hover_details == (
        "group: moment[1]",
        "conditional on: cirq.BitMaskKeyCondition(key=cirq.MeasurementKey(name='m'), index=2, target_value=0, equal_target=False, bitmask=None)",
    )


def test_cirq_adapter_preserves_nontrivial_control_values_in_hover() -> None:
    q0, q1, q2 = cirq.LineQubit.range(3)
    circuit = cirq.Circuit(cirq.X(q1).controlled_by(q0, q2, control_values=[{0, 1}, [1]]))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.kind is OperationKind.CONTROLLED_GATE
    assert operation.control_values == ((0, 1), (1,))
    assert operation.hover_details == (
        "group: moment[0]",
        "control values: (0, 1), (1)",
    )


def test_cirq_adapter_keeps_open_control_values_aligned_with_each_control_wire() -> None:
    q0, q1, q2 = cirq.LineQubit.range(3)
    circuit = cirq.Circuit(cirq.X(q2).controlled_by(q0, q1, control_values=[0, 1]))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.kind is OperationKind.CONTROLLED_GATE
    assert operation.control_wires == ("q0", "q1")
    assert operation.control_values == ((0,), (1,))


def test_cirq_adapter_preserves_native_tags_in_hover_and_metadata() -> None:
    q0 = cirq.LineQubit(0)
    circuit = cirq.Circuit(cirq.X(q0).with_tags("tag-a", "tag-b"))

    semantic_ir = CirqAdapter().to_semantic_ir(circuit, options={"explicit_matrices": False})
    operation = semantic_ir.layers[0].operations[0]

    assert operation.kind is OperationKind.GATE
    assert operation.name == "X"
    assert operation.hover_details == (
        "group: moment[0]",
        "tags: tag-a, tag-b",
    )
    assert operation.metadata["cirq_tags"] == ("tag-a", "tag-b")


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
