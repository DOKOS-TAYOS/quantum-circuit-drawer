"""Long Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import cirq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a long Cirq circuit in an interactive Matplotlib window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> cirq.Circuit:
    q0, q1, q2, q3, q4 = cirq.LineQubit.range(5)
    return cirq.Circuit(
        cirq.Moment(
            cirq.H(q0),
            cirq.rx(0.37)(q1),
            cirq.ry(1.11)(q2),
            cirq.rz(0.48)(q3),
            cirq.X(q4),
        ),
        cirq.Moment(
            cirq.CNOT(q0, q1),
            cirq.SWAP(q2, q4),
        ),
        cirq.Moment(
            cirq.CZ(q1, q3),
        ),
        cirq.Moment(
            cirq.Z(q4).controlled_by(q3),
            cirq.Y(q1),
        ),
        cirq.Moment(
            cirq.X(q3).controlled_by(q0, q2),
        ),
        cirq.Moment(
            cirq.rz(0.72)(q4),
            cirq.SWAP(q0, q3),
        ),
        cirq.Moment(
            cirq.CNOT(q4, q2),
        ),
        cirq.Moment(
            cirq.CZ(q2, q4),
        ),
        cirq.Moment(
            cirq.rx(1.17)(q2),
            cirq.X(q0).controlled_by(q4),
        ),
        cirq.Moment(
            cirq.ry(0.83)(q1),
            cirq.CNOT(q3, q0),
        ),
        cirq.Moment(
            cirq.SWAP(q1, q2),
        ),
        cirq.Moment(
            cirq.rz(0.29)(q4),
            cirq.CZ(q0, q2),
        ),
        cirq.Moment(
            cirq.Z(q1).controlled_by(q4),
        ),
        cirq.Moment(
            cirq.rx(2.21)(q0),
            cirq.rz(1.43)(q2),
            cirq.ry(0.91)(q4),
        ),
        cirq.Moment(
            cirq.X(q4).controlled_by(q1, q3),
        ),
        cirq.Moment(
            cirq.CNOT(q4, q0),
            cirq.SWAP(q2, q3),
        ),
        cirq.Moment(
            cirq.rz(0.54)(q4),
            cirq.CZ(q2, q3),
        ),
        cirq.Moment(
            cirq.CNOT(q0, q4),
        ),
        cirq.Moment(
            cirq.measure(q4, key="alpha"),
            cirq.measure(q2, key="beta"),
        ),
        cirq.Moment(
            cirq.measure(q0, key="gamma"),
            cirq.measure(q3, key="delta"),
            cirq.measure(q1, key="epsilon"),
        ),
    )


def main() -> None:
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        framework="cirq",
        style={"font_size": 12.25, "show_params": True, "max_page_width": 11.0},
        output=args.output,
        page_slider=True,
    )

    if args.output is not None:
        print(f"Saved Cirq example to {args.output}")


if __name__ == "__main__":
    main()
