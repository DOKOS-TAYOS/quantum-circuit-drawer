"""QAOA example in PennyLane for quantum-circuit-drawer."""

from __future__ import annotations

import pennylane as qml

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


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
    run_example(
        build_tape,
        description="Render a small QAOA MaxCut circuit built with PennyLane.",
        framework="pennylane",
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="PennyLane QAOA example",
    )


if __name__ == "__main__":
    main()
