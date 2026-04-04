from __future__ import annotations

import pytest

cirq = pytest.importorskip("cirq")

from quantum_circuit_drawer.adapters.cirq_adapter import CirqAdapter
from quantum_circuit_drawer.ir.operations import OperationKind


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
