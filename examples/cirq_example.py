"""Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from pathlib import Path

import cirq

from quantum_circuit_drawer import draw_quantum_circuit


def build_circuit() -> cirq.Circuit:
    q0, q1, q2, q3 = cirq.LineQubit.range(4)
    return cirq.Circuit(
        cirq.H(q0),
        cirq.X(q1),
        cirq.Y(q2),
        cirq.Z(q3),
        cirq.CNOT(q0, q1),
        cirq.CZ(q1, q2),
        cirq.SWAP(q0, q3),
        cirq.H(q2),
        cirq.CNOT(q3, q2),
        cirq.CZ(q0, q2),
        cirq.SWAP(q1, q3),
        cirq.X(q0),
        cirq.Y(q3),
        cirq.CNOT(q2, q1),
        cirq.CZ(q3, q0),
        cirq.SWAP(q0, q2),
        cirq.Z(q1),
        cirq.CNOT(q1, q3),
        cirq.CZ(q2, q3),
        cirq.measure(q1, key="m1"),
        cirq.measure(q2, key="m2"),
        cirq.measure(q0, key="m3"),
        cirq.measure(q3, key="m4"),
    )


def main() -> None:
    circuit = build_circuit()
    output = Path("examples/output/cirq_circuit.png")

    draw_quantum_circuit(
        circuit,
        framework="cirq",
        style={"font_size": 12, "theme": "dark"},
        output=output,
    )
    print(f"Saved Cirq example to {output}")


if __name__ == "__main__":
    main()
