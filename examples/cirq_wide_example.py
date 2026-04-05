"""Wide Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from math import pi
from pathlib import Path

import cirq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a wide Cirq circuit with a horizontal slider.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> cirq.Circuit:
    qubits = cirq.LineQubit.range(6)
    circuit = cirq.Circuit()
    rounds = (
        (0.31, 0.47, 0.63, 0.82),
        (0.44, 0.58, 0.29, 0.91),
        (0.73, 0.36, 0.54, 0.67),
        (0.52, 0.78, 0.41, 0.88),
    )

    circuit.append(cirq.Moment(cirq.H(qubit) for qubit in qubits))

    for round_index, (gamma_a, gamma_b, theta_a, theta_b) in enumerate(rounds):
        circuit.append(
            cirq.Moment(
                cirq.rx(theta_a)(qubits[round_index % 6]),
                cirq.ry(theta_b)(qubits[(round_index + 2) % 6]),
                cirq.rz(gamma_a)(qubits[(round_index + 4) % 6]),
            )
        )
        circuit.append(
            cirq.Moment(
                cirq.ZZPowGate(exponent=(gamma_b + (0.08 * round_index)) / pi)(
                    qubits[0], qubits[1]
                ),
                cirq.ZZPowGate(exponent=(gamma_b + (0.08 * round_index)) / pi)(
                    qubits[2], qubits[4]
                ),
            )
        )
        circuit.append(
            cirq.Moment(
                cirq.ZZPowGate(exponent=(gamma_b + (0.08 * round_index)) / pi)(
                    qubits[1], qubits[2]
                ),
                cirq.ZZPowGate(exponent=(gamma_b + (0.08 * round_index)) / pi)(
                    qubits[4], qubits[5]
                ),
            )
        )
        circuit.append(
            cirq.Moment(
                cirq.ZZPowGate(exponent=(gamma_b + (0.08 * round_index)) / pi)(qubits[0], qubits[5])
            )
        )
        circuit.append(
            cirq.Moment(cirq.CNOT(qubits[round_index % 6], qubits[(round_index + 1) % 6]))
        )
        circuit.append(
            cirq.Moment(cirq.CZ(qubits[(round_index + 2) % 6], qubits[(round_index + 4) % 6]))
        )
        circuit.append(
            cirq.Moment(cirq.SWAP(qubits[(round_index + 1) % 6], qubits[(round_index + 3) % 6]))
        )

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
        style={"font_size": 12.0, "show_params": True, "max_page_width": 8.5},
        output=args.output,
        page_slider=True,
    )

    if args.output is not None:
        print(f"Saved Cirq wide example to {args.output}")


if __name__ == "__main__":
    main()
