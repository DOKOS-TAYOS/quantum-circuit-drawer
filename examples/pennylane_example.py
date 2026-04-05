"""Balanced PennyLane tape example for quantum-circuit-drawer."""

from __future__ import annotations

import pennylane as qml

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_tape() -> qml.tape.QuantumTape:
    with qml.tape.QuantumTape() as tape:
        qml.Hadamard(wires=0)
        qml.RY(0.61, wires=1)
        qml.RZ(0.28, wires=2)
        qml.PauliX(wires=3)

        qml.CNOT(wires=[0, 1])
        qml.IsingZZ(0.72, wires=[1, 3])
        qml.SWAP(wires=[0, 2])
        qml.CRZ(0.44, wires=[2, 3])
        qml.CNOT(wires=[3, 0])
        qml.RY(0.39, wires=1)

        qml.probs(wires=[0])
        qml.probs(wires=[2])
        qml.probs(wires=[3])
        qml.probs(wires=[1])
    return tape


def main() -> None:
    run_example(
        build_tape,
        description="Render a balanced PennyLane tape in an interactive Matplotlib window.",
        framework="pennylane",
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="PennyLane example",
    )


if __name__ == "__main__":
    main()
