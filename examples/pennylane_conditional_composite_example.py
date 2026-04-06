"""PennyLane demo showing mid-measurement conditionals and composite expansion."""

from __future__ import annotations

import pennylane as qml

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_tape() -> qml.tape.QuantumTape:
    with qml.tape.QuantumTape() as tape:
        qml.QFT(wires=[0, 1, 2])
        measured_bit = qml.measure(0)
        qml.cond(measured_bit, qml.RY)(0.42, wires=3)
        qml.cond(measured_bit, qml.CNOT)(wires=[1, 3])
        qml.probs(wires=[3])
    return tape


def main() -> None:
    run_example(
        build_tape,
        description="Render a PennyLane demo with mid-circuit conditions and expanded composite operations.",
        framework="pennylane",
        style=demo_style(max_page_width=7.0),
        page_slider=False,
        composite_mode="expand",
        saved_label="PennyLane conditional/composite example",
    )


if __name__ == "__main__":
    main()
