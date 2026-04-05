"""Grover search example in Qiskit for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a small Grover search circuit built with Qiskit.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(2, "q")
    classical = ClassicalRegister(2, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_grover_demo")

    circuit.h(0)
    circuit.h(1)

    circuit.cz(0, 1)

    circuit.h(0)
    circuit.h(1)
    circuit.x(0)
    circuit.x(1)
    circuit.h(1)
    circuit.cx(0, 1)
    circuit.h(1)
    circuit.x(0)
    circuit.x(1)
    circuit.h(0)
    circuit.h(1)

    circuit.measure(0, classical[0])
    circuit.measure(1, classical[1])
    return circuit


def main() -> None:
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        style={"font_size": 12.0, "show_params": True, "max_page_width": 6.5},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved Qiskit Grover example to {args.output}")


if __name__ == "__main__":
    main()
