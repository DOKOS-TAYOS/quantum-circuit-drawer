"""Showcase PennyLane example focused on terminal-output boxes."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from pennylane import cond, measure
from pennylane.measurements import counts, density_matrix, expval, probs
from pennylane.ops import CNOT, RX, RY, Hadamard, PauliZ
from pennylane.tape import QuantumTape

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402


def build_tape(*, qubit_count: int, motif_count: int) -> QuantumTape:
    """Build a PennyLane tape that highlights mid-measure and terminal outputs."""

    with QuantumTape() as tape:
        Hadamard(wires=0)
        CNOT(wires=[0, 1])
        RX(0.25, wires=2)

        measured_bit = measure(0)
        cond(measured_bit, RX)(0.45, wires=1)

        for step in range(motif_count):
            target_wire = 2 + (step % max(1, qubit_count - 2))
            RY(0.16 * float(step + 1), wires=target_wire)

        probs(wires=[0, 1])
        counts(wires=[0, 1])
        expval(PauliZ(wires=min(2, qubit_count - 1)))
        density_matrix(wires=[qubit_count - 2, qubit_count - 1])
    return tape


def main() -> None:
    """Render a PennyLane tape with mid-measurement and terminal outputs."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_tape(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                output=OutputOptions(output_path=args.output, show=args.show),
            ),
        )
        if args.output is not None:
            print(f"Saved pennylane-terminal-outputs-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a PennyLane tape with qml.cond(...), mid-measurement, and terminal outputs."
    )
    parser.add_argument("--qubits", type=int, default=4, help="Number of qubits in the tape.")
    parser.add_argument(
        "--motifs",
        type=int,
        default=3,
        help="Extra rotation motifs to append before the terminal outputs.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
