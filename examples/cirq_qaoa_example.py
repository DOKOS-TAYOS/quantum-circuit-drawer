"""QAOA example in Cirq for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from math import pi
from pathlib import Path

import cirq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a small QAOA MaxCut circuit built with Cirq.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> cirq.Circuit:
    qubits = cirq.LineQubit.range(4)
    gammas = (0.45, 0.73)
    betas = (0.31, 0.52)
    circuit = cirq.Circuit()

    circuit.append(cirq.Moment(cirq.H(qubit) for qubit in qubits))

    for gamma, beta in zip(gammas, betas, strict=True):
        circuit.append(
            cirq.Moment(
                cirq.ZZPowGate(exponent=gamma / pi)(qubits[0], qubits[1]),
                cirq.ZZPowGate(exponent=gamma / pi)(qubits[2], qubits[3]),
            )
        )
        circuit.append(
            cirq.Moment(
                cirq.ZZPowGate(exponent=gamma / pi)(qubits[1], qubits[2]),
                cirq.ZZPowGate(exponent=gamma / pi)(qubits[3], qubits[0]),
            )
        )
        circuit.append(cirq.Moment(cirq.rx(2.0 * beta)(qubit) for qubit in qubits))

    circuit.append(
        cirq.Moment(cirq.measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits))
    )
    return circuit


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
        print(f"Saved Cirq QAOA example to {args.output}")


if __name__ == "__main__":
    main()
