"""Cirq demo showing classical conditions and composite expansion."""

from __future__ import annotations

import cirq

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def _circuit_block(*, qubits: tuple[cirq.Qid, cirq.Qid], angle: float) -> cirq.Circuit:
    first, second = qubits
    return cirq.Circuit(
        cirq.H(first),
        cirq.CNOT(first, second),
        cirq.rz(angle)(second),
    )


def build_circuit() -> cirq.Circuit:
    q0, q1, q2, q3 = cirq.LineQubit.range(4)
    prepare = cirq.CircuitOperation(_circuit_block(qubits=(q0, q1), angle=0.31).freeze())
    conditional = cirq.CircuitOperation(_circuit_block(qubits=(q2, q3), angle=0.47).freeze())

    return cirq.Circuit(
        prepare,
        cirq.measure(q1, key="flag"),
        conditional.with_classical_controls("flag"),
        cirq.X(q3).with_classical_controls("flag"),
    )


def main() -> None:
    run_example(
        build_circuit,
        description="Render a Cirq demo with classical control and expanded circuit operations.",
        framework="cirq",
        style=demo_style(max_page_width=7.0),
        page_slider=False,
        composite_mode="expand",
        saved_label="Cirq conditional/composite example",
    )


if __name__ == "__main__":
    main()
