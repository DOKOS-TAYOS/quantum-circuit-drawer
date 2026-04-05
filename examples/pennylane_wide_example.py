"""Wide PennyLane tape example for quantum-circuit-drawer."""

from __future__ import annotations

import pennylane as qml

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_tape() -> qml.tape.QuantumTape:
    edges = ((0, 1), (1, 2), (2, 4), (4, 5), (0, 5))
    rounds = (
        (0.31, 0.47, 0.63, 0.82),
        (0.44, 0.58, 0.29, 0.91),
        (0.73, 0.36, 0.54, 0.67),
        (0.52, 0.78, 0.41, 0.88),
    )

    with qml.tape.QuantumTape() as tape:
        for wire in range(6):
            qml.Hadamard(wires=wire)

        for round_index, (gamma_a, gamma_b, theta_a, theta_b) in enumerate(rounds):
            qml.RX(theta_a, wires=round_index % 6)
            qml.RY(theta_b, wires=(round_index + 2) % 6)
            qml.RZ(gamma_a, wires=(round_index + 4) % 6)

            for left, right in edges:
                qml.IsingZZ(gamma_b + (0.08 * round_index), wires=[left, right])

            qml.CNOT(wires=[round_index % 6, (round_index + 1) % 6])
            qml.CZ(wires=[(round_index + 2) % 6, (round_index + 4) % 6])
            qml.SWAP(wires=[(round_index + 1) % 6, (round_index + 3) % 6])

        for wire in range(6):
            qml.probs(wires=[wire])
    return tape


def main() -> None:
    run_example(
        build_tape,
        description="Render a wide PennyLane tape with a horizontal slider.",
        framework="pennylane",
        style=demo_style(max_page_width=8.5),
        page_slider=True,
        saved_label="PennyLane wide example",
    )


if __name__ == "__main__":
    main()
