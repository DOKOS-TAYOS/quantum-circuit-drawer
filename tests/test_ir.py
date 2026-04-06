from __future__ import annotations

import pytest

from quantum_circuit_drawer.ir.circuit import CircuitIR, LayerIR
from quantum_circuit_drawer.ir.measurements import MeasurementIR
from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.ir.wires import WireIR, WireKind


def test_layer_ir_normalizes_operations_and_circuit_counts_wires() -> None:
    layer = LayerIR(
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
    circuit = CircuitIR(
        quantum_wires=[
            WireIR(id="q0", index=0, kind=WireKind.QUANTUM, label="q0"),
            WireIR(id="q1", index=1, kind=WireKind.QUANTUM, label="q1"),
        ],
        classical_wires=[WireIR(id="c0", index=0, kind=WireKind.CLASSICAL, label="c0")],
        layers=[layer],
    )

    assert isinstance(layer.operations, tuple)
    assert circuit.quantum_wire_count == 2
    assert circuit.classical_wire_count == 1
    assert circuit.total_wire_count == 3


def test_circuit_ir_rejects_duplicate_wire_ids() -> None:
    with pytest.raises(ValueError, match="wire ids must be unique"):
        CircuitIR(
            quantum_wires=[WireIR(id="q0", index=0, kind=WireKind.QUANTUM)],
            classical_wires=[WireIR(id="q0", index=0, kind=WireKind.CLASSICAL)],
        )


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


def test_operation_ir_rejects_empty_name_and_missing_targets_for_non_barriers() -> None:
    with pytest.raises(ValueError, match="operation name cannot be empty"):
        OperationIR(kind=OperationKind.GATE, name="", target_wires=("q0",))

    with pytest.raises(ValueError, match="operation must reference at least one target wire"):
        OperationIR(kind=OperationKind.GATE, name="H", target_wires=())

    barrier = OperationIR(kind=OperationKind.BARRIER, name="BARRIER", target_wires=())

    assert barrier.target_wires == ()


def test_operation_ir_occupied_wire_ids_preserve_first_occurrence() -> None:
    operation = OperationIR(
        kind=OperationKind.CONTROLLED_GATE,
        name="X",
        target_wires=("q1", "q1"),
        control_wires=("q0", "q1"),
    )

    assert operation.occupied_wire_ids == ("q0", "q1")


def test_measurement_ir_requires_classical_target_and_tracks_classical_slot() -> None:
    with pytest.raises(ValueError, match="measurement operations require a classical_target"):
        MeasurementIR(
            kind=OperationKind.MEASUREMENT,
            name="M",
            target_wires=("q0",),
            classical_target=None,
        )

    measurement = MeasurementIR(
        kind=OperationKind.MEASUREMENT,
        name="M",
        target_wires=("q0",),
        classical_target="c0",
    )

    assert measurement.kind is OperationKind.MEASUREMENT
    assert measurement.occupied_wire_ids == ("q0", "classical:c0")


def test_wire_ir_defaults_label_and_rejects_empty_ids() -> None:
    wire = WireIR(id="q0", index=0, kind=WireKind.QUANTUM)

    assert wire.label == "q0"

    with pytest.raises(ValueError, match="wire id cannot be empty"):
        WireIR(id="", index=0, kind=WireKind.QUANTUM)
