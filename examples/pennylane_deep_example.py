"""Deep PennyLane tape example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import pennylane as qml

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a deep PennyLane tape in a compact interactive window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_tape() -> qml.tape.QuantumTape:
    with qml.tape.QuantumTape() as tape:
        for layer_index in range(10):
            qml.RX(0.22 + (0.11 * layer_index), wires=0)
            qml.RY(0.35 + (0.07 * layer_index), wires=1)
            qml.RZ(0.19 + (0.05 * layer_index), wires=2)
            qml.CNOT(wires=[layer_index % 3, (layer_index + 1) % 3])

            if layer_index % 2 == 0:
                qml.IsingZZ(0.42 + (0.04 * layer_index), wires=[0, 2])
            else:
                qml.SWAP(wires=[0, 1])

        qml.probs(wires=[0])
        qml.probs(wires=[1])
        qml.probs(wires=[2])
    return tape


def main() -> None:
    args = parse_args()
    tape = build_tape()

    draw_quantum_circuit(
        tape,
        framework="pennylane",
        style={"font_size": 12.0, "show_params": True, "max_page_width": 6.0},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved PennyLane deep example to {args.output}")


if __name__ == "__main__":
    main()
