"""Deep Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from math import pi

import cirq

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> cirq.Circuit:
    q0, q1, q2 = cirq.LineQubit.range(3)
    circuit = cirq.Circuit()

    for layer_index in range(10):
        circuit.append(
            cirq.Moment(
                cirq.rx(0.22 + (0.11 * layer_index))(q0),
                cirq.ry(0.35 + (0.07 * layer_index))(q1),
                cirq.rz(0.19 + (0.05 * layer_index))(q2),
            )
        )
        circuit.append(cirq.CNOT((q0, q1, q2)[layer_index % 3], (q1, q2, q0)[layer_index % 3]))
        if layer_index % 2 == 0:
            circuit.append(cirq.ZZPowGate(exponent=(0.42 + (0.04 * layer_index)) / pi)(q0, q2))
        else:
            circuit.append(cirq.SWAP(q0, q1))

    circuit.append(
        cirq.Moment(
            cirq.measure(q0, key="c0"), cirq.measure(q1, key="c1"), cirq.measure(q2, key="c2")
        )
    )
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a deep Cirq circuit in a compact interactive window.",
        framework="cirq",
        style=demo_style(max_page_width=6.0),
        page_slider=False,
        saved_label="Cirq deep example",
    )


if __name__ == "__main__":
    main()
