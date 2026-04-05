"""QAOA example in Cirq for quantum-circuit-drawer."""

from __future__ import annotations

from math import pi

import cirq

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


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
    run_example(
        build_circuit,
        description="Render a small QAOA MaxCut circuit built with Cirq.",
        framework="cirq",
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="Cirq QAOA example",
    )


if __name__ == "__main__":
    main()
