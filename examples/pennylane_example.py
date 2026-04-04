"""Long PennyLane tape example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import pennylane as qml

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a long PennyLane tape in an interactive Matplotlib window."
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
        qml.RX(0.37, wires=1)
        qml.RY(1.11, wires=2)
        qml.RZ(0.48, wires=3)
        qml.PauliX(wires=4)

        qml.CNOT(wires=[0, 1])
        qml.CZ(wires=[1, 3])
        qml.SWAP(wires=[2, 4])
        qml.CRZ(0.72, wires=[3, 4])
        qml.Toffoli(wires=[0, 2, 3])

        qml.SWAP(wires=[1, 4])
        qml.RZ(0.52, wires=4)
        qml.CNOT(wires=[4, 2])
        qml.CRY(0.83, wires=[2, 1])
        qml.SWAP(wires=[0, 3])

        qml.CZ(wires=[2, 4])
        qml.CRX(1.17, wires=[1, 2])
        qml.RX(0.66, wires=3)
        qml.CNOT(wires=[3, 0])
        qml.SWAP(wires=[1, 2])

        qml.CRX(0.29, wires=[0, 4])
        qml.CRY(0.41, wires=[4, 1])
        qml.RX(2.21, wires=0)
        qml.RZ(1.43, wires=2)
        qml.RY(0.91, wires=4)

        qml.Toffoli(wires=[1, 3, 4])
        qml.CNOT(wires=[4, 0])
        qml.CZ(wires=[0, 2])

        qml.probs(wires=[4])
        qml.probs(wires=[2])
        qml.probs(wires=[0])
        qml.probs(wires=[3])
        qml.probs(wires=[1])
    return tape


def main() -> None:
    args = parse_args()
    tape = build_tape()

    draw_quantum_circuit(
        tape,
        framework="pennylane",
        style={
            "font_size": 12.25,
            "show_params": True,
            "wire_spacing": 1.35,
            "max_page_width": 10.75,
        },
        output=args.output,
        page_slider=True,
    )

    if args.output is not None:
        print(f"Saved PennyLane example to {args.output}")


if __name__ == "__main__":
    main()
