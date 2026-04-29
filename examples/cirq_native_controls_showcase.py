"""Showcase Cirq example focused on native controls and structure."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from cirq.circuits import Circuit, CircuitOperation, FrozenCircuit, Moment
from cirq.devices import LineQubit
from cirq.ops import CNOT, H, X, Z, measure, rx

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402

DEFAULT_FIGSIZE: tuple[float, float] = (10.1, 5.5)


def build_circuit(*, qubit_count: int, motif_count: int) -> Circuit:
    """Build a Cirq circuit that highlights native controls and provenance."""

    qubits = LineQubit.range(qubit_count)
    moments: list[Moment] = [
        Moment(H(qubits[0]), H(qubits[1]), rx(0.35)(qubits[2])),
        Moment(X(qubits[2]).controlled_by(qubits[0], control_values=[0])),
        Moment(Z(qubits[3]).controlled_by(qubits[0], qubits[1], control_values=[0, 1])),
        Moment(measure(qubits[0], key="m")),
        Moment(X(qubits[1]).with_classical_controls("m")),
        Moment(_build_circuit_operation(qubits[2], qubits[3])),
    ]

    for step in range(motif_count):
        target = 2 + (step % max(1, qubit_count - 2))
        moments.append(Moment(rx(0.18 * float(step + 1))(qubits[target])))

    moments.append(Moment(measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits)))
    return Circuit(*moments)


def _build_circuit_operation(control: LineQubit, target: LineQubit) -> CircuitOperation:
    nested = FrozenCircuit(H(control), CNOT(control, target))
    return CircuitOperation(nested)


def main() -> None:
    """Render a Cirq circuit with open controls and classical control."""

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
            print(f"Saved cirq-native-controls-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a Cirq circuit with native controls, classical control, and CircuitOperation provenance."
    )
    parser.add_argument("--qubits", type=int, default=4, help="Number of qubits to allocate.")
    parser.add_argument(
        "--motifs",
        type=int,
        default=3,
        help="Additional native-control motifs to append after the structural core.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
