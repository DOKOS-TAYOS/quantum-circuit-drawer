"""Framework-free workflow built directly from the public CircuitIR types."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402
from quantum_circuit_drawer.ir import (  # noqa: E402
    CircuitIR,
    LayerIR,
    MeasurementIR,
    OperationIR,
    OperationKind,
    WireIR,
    WireKind,
)

DEFAULT_FIGSIZE: tuple[float, float] = (10.6, 5.8)


def build_circuit(*, qubit_count: int, motif_count: int) -> CircuitIR:
    """Build a public IR circuit without using any external framework."""

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
    for step in range(motif_count):
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


def main() -> None:
    """Render a circuit built directly from the public IR types."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved ir-basic-workflow to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a workflow built directly from the public CircuitIR types."
    )
    parser.add_argument(
        "--qubits", type=int, default=4, help="Number of qubits to include in the IR circuit."
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=3,
        help="Extra phase motifs to add after the first two logical layers.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
