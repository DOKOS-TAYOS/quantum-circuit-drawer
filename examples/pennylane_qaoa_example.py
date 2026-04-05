"""QAOA example in PennyLane for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import pennylane as qml

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a small QAOA MaxCut circuit built with PennyLane.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_tape() -> qml.tape.QuantumTape:
    edges = ((0, 1), (1, 2), (2, 3), (3, 0))
    gammas = (0.45, 0.73)
    betas = (0.31, 0.52)

    with qml.tape.QuantumTape() as tape:
        for wire in range(4):
            qml.Hadamard(wires=wire)

        for gamma, beta in zip(gammas, betas, strict=True):
            for left, right in edges:
                qml.IsingZZ(gamma, wires=[left, right])
            for wire in range(4):
                qml.RX(2.0 * beta, wires=wire)

        for wire in range(4):
            qml.probs(wires=[wire])
    return tape


def main() -> None:
    args = parse_args()
    tape = build_tape()

    draw_quantum_circuit(
        tape,
        framework="pennylane",
        style={"font_size": 12.0, "show_params": True, "max_page_width": 7.5},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved PennyLane QAOA example to {args.output}")


if __name__ == "__main__":
    main()
