"""Grover search example in PennyLane for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import pennylane as qml

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a small Grover search circuit built with PennyLane."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_tape() -> qml.tape.QuantumTape:
    with qml.tape.QuantumTape() as tape:
        qml.Hadamard(wires=0)
        qml.Hadamard(wires=1)

        qml.CZ(wires=[0, 1])

        qml.Hadamard(wires=0)
        qml.Hadamard(wires=1)
        qml.PauliX(wires=0)
        qml.PauliX(wires=1)
        qml.Hadamard(wires=1)
        qml.CNOT(wires=[0, 1])
        qml.Hadamard(wires=1)
        qml.PauliX(wires=0)
        qml.PauliX(wires=1)
        qml.Hadamard(wires=0)
        qml.Hadamard(wires=1)

        qml.probs(wires=[0])
        qml.probs(wires=[1])
    return tape


def main() -> None:
    args = parse_args()
    tape = build_tape()

    draw_quantum_circuit(
        tape,
        framework="pennylane",
        style={"font_size": 12.0, "show_params": True, "max_page_width": 6.5},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved PennyLane Grover example to {args.output}")


if __name__ == "__main__":
    main()
