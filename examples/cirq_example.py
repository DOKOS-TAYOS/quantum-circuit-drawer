"""Balanced Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from math import pi

import cirq

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> cirq.Circuit:
    q0, q1, q2, q3 = cirq.LineQubit.range(4)
    zz_gate = cirq.ZZPowGate(exponent=0.72 / pi)
    return cirq.Circuit(
        cirq.Moment(cirq.H(q0), cirq.ry(0.61)(q1), cirq.rz(0.28)(q2), cirq.X(q3)),
        cirq.Moment(cirq.CNOT(q0, q1)),
        cirq.Moment(zz_gate(q1, q3)),
        cirq.Moment(cirq.SWAP(q0, q2)),
        cirq.Moment(cirq.Z(q3).controlled_by(q2)),
        cirq.Moment(cirq.CNOT(q3, q0), cirq.ry(0.39)(q1)),
        cirq.Moment(cirq.measure(q0, key="c0"), cirq.measure(q2, key="c1")),
        cirq.Moment(cirq.measure(q3, key="c2"), cirq.measure(q1, key="c3")),
    )


def main() -> None:
    run_example(
        build_circuit,
        description="Render a balanced Cirq circuit in an interactive Matplotlib window.",
        framework="cirq",
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="Cirq example",
    )


if __name__ == "__main__":
    main()
