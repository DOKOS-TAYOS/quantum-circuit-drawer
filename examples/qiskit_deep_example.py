"""Deep Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a deep Qiskit circuit in a compact interactive window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(3, "q")
    classical = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_deep_demo")

    for layer_index in range(10):
        circuit.rx(0.22 + (0.11 * layer_index), 0)
        circuit.ry(0.35 + (0.07 * layer_index), 1)
        circuit.rz(0.19 + (0.05 * layer_index), 2)
        circuit.cx(layer_index % 3, (layer_index + 1) % 3)

        if layer_index % 2 == 0:
            circuit.rzz(0.42 + (0.04 * layer_index), 0, 2)
        else:
            circuit.swap(0, 1)

    circuit.measure(0, classical[0])
    circuit.measure(1, classical[1])
    circuit.measure(2, classical[2])
    return circuit


def main() -> None:
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        style={"font_size": 12.0, "show_params": True, "max_page_width": 6.0},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved Qiskit deep example to {args.output}")


if __name__ == "__main__":
    main()
