"""Wide Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a wide Qiskit circuit with a horizontal slider.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(6, "q")
    classical = ClassicalRegister(6, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_wide_demo")

    for wire in range(6):
        circuit.h(wire)

    rounds = (
        (0.31, 0.47, 0.63, 0.82),
        (0.44, 0.58, 0.29, 0.91),
        (0.73, 0.36, 0.54, 0.67),
        (0.52, 0.78, 0.41, 0.88),
    )
    edges = ((0, 1), (1, 2), (2, 4), (4, 5), (0, 5))

    for round_index, (gamma_a, gamma_b, theta_a, theta_b) in enumerate(rounds):
        circuit.rx(theta_a, round_index % 6)
        circuit.ry(theta_b, (round_index + 2) % 6)
        circuit.rz(gamma_a, (round_index + 4) % 6)

        for left, right in edges:
            circuit.rzz(gamma_b + (0.08 * round_index), left, right)

        circuit.cx(round_index % 6, (round_index + 1) % 6)
        circuit.cz((round_index + 2) % 6, (round_index + 4) % 6)
        circuit.swap((round_index + 1) % 6, (round_index + 3) % 6)
        circuit.barrier()

    for wire in range(6):
        circuit.measure(wire, classical[wire])
    return circuit


def main() -> None:
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        style={"font_size": 12.0, "show_params": True, "max_page_width": 8.5},
        output=args.output,
        page_slider=True,
    )

    if args.output is not None:
        print(f"Saved Qiskit wide example to {args.output}")


if __name__ == "__main__":
    main()
