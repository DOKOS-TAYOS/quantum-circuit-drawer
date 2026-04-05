"""Grover search example in Cirq for quantum-circuit-drawer."""

from __future__ import annotations

import cirq

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> cirq.Circuit:
    q0, q1 = cirq.LineQubit.range(2)
    return cirq.Circuit(
        cirq.Moment(cirq.H(q0), cirq.H(q1)),
        cirq.Moment(cirq.CZ(q0, q1)),
        cirq.Moment(cirq.H(q0), cirq.H(q1)),
        cirq.Moment(cirq.X(q0), cirq.X(q1)),
        cirq.Moment(cirq.H(q1)),
        cirq.Moment(cirq.CNOT(q0, q1)),
        cirq.Moment(cirq.H(q1)),
        cirq.Moment(cirq.X(q0), cirq.X(q1)),
        cirq.Moment(cirq.H(q0), cirq.H(q1)),
        cirq.Moment(cirq.measure(q0, key="c0"), cirq.measure(q1, key="c1")),
    )


def main() -> None:
    run_example(
        build_circuit,
        description="Render a small Grover search circuit built with Cirq.",
        framework="cirq",
        style=demo_style(max_page_width=6.5),
        page_slider=False,
        saved_label="Cirq Grover example",
    )


if __name__ == "__main__":
    main()
