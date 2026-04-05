"""Grover search example in PennyLane for quantum-circuit-drawer."""

from __future__ import annotations

import pennylane as qml

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


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
    run_example(
        build_tape,
        description="Render a small Grover search circuit built with PennyLane.",
        framework="pennylane",
        style=demo_style(max_page_width=6.5),
        page_slider=False,
        saved_label="PennyLane Grover example",
    )


if __name__ == "__main__":
    main()
