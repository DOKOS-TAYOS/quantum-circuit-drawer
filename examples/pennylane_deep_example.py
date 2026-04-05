"""Deep PennyLane tape example for quantum-circuit-drawer."""

from __future__ import annotations

import pennylane as qml

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


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
    run_example(
        build_tape,
        description="Render a deep PennyLane tape in a compact interactive window.",
        framework="pennylane",
        style=demo_style(max_page_width=6.0),
        page_slider=False,
        saved_label="PennyLane deep example",
    )


if __name__ == "__main__":
    main()
