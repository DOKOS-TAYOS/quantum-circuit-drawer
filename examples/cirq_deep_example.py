"""Deep Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from math import pi
from pathlib import Path

import cirq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a deep Cirq circuit in a compact interactive window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


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
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        framework="cirq",
        style={"font_size": 12.0, "show_params": True, "max_page_width": 6.0},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved Cirq deep example to {args.output}")


if __name__ == "__main__":
    main()
