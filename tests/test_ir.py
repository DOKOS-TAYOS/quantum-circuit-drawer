from __future__ import annotations

from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind


def test_circuit_ir_counts_quantum_and_classical_wires() -> None:
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0")],
        layers=[
            LayerIR(
                operations=[
                    OperationIR(kind=OperationKind.GATE, name="H", target_wires=("q0",)),
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=("q0",),
                        classical_target="c0",
                    ),
                ]
            )
        ],
    )

    assert circuit.quantum_wire_count == 2
    assert circuit.classical_wire_count == 1
    assert circuit.total_wire_count == 3


def test_operation_ir_normalizes_tuple_fields() -> None:
    operation = OperationIR(
        kind=OperationKind.CONTROLLED_GATE,
        name="X",
        target_wires=["q1"],
        control_wires=["q0"],
        parameters=[3.1415],
    )

    assert operation.target_wires == ("q1",)
    assert operation.control_wires == ("q0",)
    assert operation.parameters == (3.1415,)
