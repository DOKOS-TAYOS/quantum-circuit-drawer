"""Grover search example in Cirq for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import cirq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a small Grover search circuit built with Cirq.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


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
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        framework="cirq",
        style={"font_size": 12.0, "show_params": True, "max_page_width": 6.5},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved Cirq Grover example to {args.output}")


if __name__ == "__main__":
    main()
