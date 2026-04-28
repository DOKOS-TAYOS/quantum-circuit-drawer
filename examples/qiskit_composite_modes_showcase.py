"""Qiskit showcase centered on compact versus expanded composites."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.synthesis.qft import synth_qft_full

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

DEFAULT_FIGSIZE: tuple[float, float] = (8.8, 4.8)


def build_circuit(*, qubit_count: int, motif_count: int) -> QuantumCircuit:
    """Build a Qiskit circuit with a reusable composite block."""

    qft_width = min(3, qubit_count)
    circuit = QuantumCircuit(qubit_count, qubit_count, name="qiskit_composite_modes_showcase")
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.append(synth_qft_full(qft_width).to_instruction(label="QFT"), range(qft_width))
    for step in range(motif_count):
        target = 1 + (step % max(1, qubit_count - 1))
        circuit.ry(0.14 * float(step + 1), target)
    circuit.cz(qubit_count - 2, qubit_count - 1)
    circuit.measure(range(qubit_count), range(qubit_count))
    return circuit


def main() -> None:
    """Render the same Qiskit workflow with the selected composite mode."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(composite_mode=args.composite_mode),
                ),
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved qiskit-composite-modes-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a Qiskit circuit that is useful for comparing compact and expanded composites."
    )
    parser.add_argument("--qubits", type=int, default=5, help="Number of qubits to allocate.")
    parser.add_argument(
        "--motifs",
        type=int,
        default=4,
        help="Extra single-qubit motifs to append after the composite block.",
    )
    parser.add_argument(
        "--composite-mode",
        choices=("compact", "expand"),
        default="compact",
        help="How the QFT composite block should be shown.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
