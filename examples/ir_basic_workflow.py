"""Framework-free workflow built directly from the public CircuitIR types."""

from __future__ import annotations

try:
    from examples._shared import ExampleRequest, build_draw_config, parse_example_args
except ImportError:
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import draw_quantum_circuit
from quantum_circuit_drawer.ir import (
    CircuitIR,
    LayerIR,
    MeasurementIR,
    OperationIR,
    OperationKind,
    WireIR,
    WireKind,
)


def build_circuit(request: ExampleRequest) -> CircuitIR:
    """Build a public IR circuit without using any external framework."""

    qubit_count = max(3, request.qubits)
    quantum_wires = [
        WireIR(id=f"q{index}", index=index, kind=WireKind.QUANTUM, label=f"q{index}")
        for index in range(qubit_count)
    ]
    classical_wires = [
        WireIR(id=f"c{index}", index=index, kind=WireKind.CLASSICAL, label=f"c{index}")
        for index in range(qubit_count)
    ]
    layers = [
        LayerIR(
            operations=[
                OperationIR(
                    kind=OperationKind.GATE,
                    name="H",
                    target_wires=["q0"],
                )
            ]
        ),
        LayerIR(
            operations=[
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name="X",
                    control_wires=["q0"],
                    target_wires=["q1"],
                )
            ]
        ),
    ]
    for step in range(_motif_count(request, qubit_count)):
        target_wire = 1 + (step % max(1, qubit_count - 1))
        layers.append(
            LayerIR(
                operations=[
                    OperationIR(
                        kind=OperationKind.GATE,
                        name="RZ",
                        target_wires=[f"q{target_wire}"],
                        parameters=(0.2 * float(step + 1),),
                    )
                ]
            )
        )
    for index in range(qubit_count):
        layers.append(
            LayerIR(
                operations=[
                    MeasurementIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=[f"q{index}"],
                        classical_target=f"c{index}",
                    )
                ]
            )
        )
    return CircuitIR(
        quantum_wires=quantum_wires,
        classical_wires=classical_wires,
        layers=layers,
        name="ir_basic_workflow",
    )


def _motif_count(request: ExampleRequest, qubit_count: int) -> int:
    return max(1, min(request.columns, qubit_count + 1))


def main() -> None:
    """Run the public IR workflow demo as a normal user-facing script."""

    request = parse_example_args(
        description="Render a workflow built directly from the public CircuitIR types.",
        default_qubits=4,
        default_columns=3,
        columns_help="Extra phase motifs to add to the public IR circuit",
    )
    result = draw_quantum_circuit(
        build_circuit(request),
        config=build_draw_config(request, framework="ir"),
    )
    if hasattr(result.primary_figure, "set_label"):
        result.primary_figure.set_label("ir-basic-workflow")
    if request.output is not None:
        print(f"Saved ir-basic-workflow to {request.output}")


if __name__ == "__main__":
    main()
