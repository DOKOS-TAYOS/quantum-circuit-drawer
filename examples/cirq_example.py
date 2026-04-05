"""Balanced Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from math import pi
from pathlib import Path

import cirq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a balanced Cirq circuit in an interactive Matplotlib window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


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
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        framework="cirq",
        style={"font_size": 12.0, "show_params": True, "max_page_width": 7.5},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved Cirq example to {args.output}")


if __name__ == "__main__":
    main()
