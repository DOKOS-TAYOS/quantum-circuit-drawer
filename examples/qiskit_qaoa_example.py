"""QAOA example in Qiskit for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a small QAOA MaxCut circuit built with Qiskit.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(4, "q")
    classical = ClassicalRegister(4, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_qaoa_demo")

    edges = ((0, 1), (1, 2), (2, 3), (3, 0))
    gammas = (0.45, 0.73)
    betas = (0.31, 0.52)

    for wire in range(4):
        circuit.h(wire)

    for gamma, beta in zip(gammas, betas, strict=True):
        for left, right in edges:
            circuit.rzz(gamma, left, right)
        for wire in range(4):
            circuit.rx(2.0 * beta, wire)

    for wire in range(4):
        circuit.measure(wire, classical[wire])
    return circuit


def main() -> None:
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        style={"font_size": 12.0, "show_params": True, "max_page_width": 7.5},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved Qiskit QAOA example to {args.output}")


if __name__ == "__main__":
    main()
