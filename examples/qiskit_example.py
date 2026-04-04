"""Long Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a long Qiskit circuit in an interactive Matplotlib window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(6, "q")
    alpha = ClassicalRegister(3, "alpha")
    beta = ClassicalRegister(3, "beta")
    circuit = QuantumCircuit(quantum, alpha, beta, name="qiskit_deep_demo")

    circuit.h(0)
    circuit.rx(0.37, 1)
    circuit.ry(1.11, 2)
    circuit.rz(0.48, 3)
    circuit.x(4)
    circuit.y(5)

    circuit.cx(0, 1)
    circuit.cz(1, 3)
    circuit.swap(2, 4)
    circuit.barrier(0, 1, 2)

    circuit.crz(0.72, 3, 4)
    circuit.ccx(0, 2, 3)
    circuit.swap(1, 5)
    circuit.rz(0.52, 4)
    circuit.cx(4, 2)
    circuit.barrier(2, 3, 4, 5)

    circuit.ry(0.83, 1)
    circuit.swap(0, 3)
    circuit.cz(2, 5)
    circuit.crx(1.17, 1, 2)
    circuit.cx(5, 4)
    circuit.barrier()

    circuit.rx(0.66, 3)
    circuit.cx(3, 0)
    circuit.swap(1, 2)
    circuit.rzz(0.29, 0, 4)
    circuit.cy(4, 1)
    circuit.cz(5, 2)
    circuit.barrier()

    circuit.rx(2.21, 0)
    circuit.rz(1.43, 2)
    circuit.ry(0.91, 4)
    circuit.ccx(1, 3, 5)
    circuit.cx(5, 0)
    circuit.swap(2, 4)
    circuit.barrier(0, 2, 4, 5)

    circuit.crx(0.54, 0, 5)
    circuit.crz(1.31, 2, 3)
    circuit.swap(1, 4)
    circuit.ry(1.05, 5)
    circuit.cx(4, 3)
    circuit.cz(0, 2)

    circuit.measure(5, alpha[0])
    circuit.measure(3, alpha[1])
    circuit.measure(1, alpha[2])
    circuit.measure(0, beta[0])
    circuit.measure(2, beta[1])
    circuit.measure(4, beta[2])
    return circuit


def main() -> None:
    args = parse_args()
    circuit = build_circuit()

    draw_quantum_circuit(
        circuit,
        style={"font_size": 12.5, "show_params": True, "max_page_width": 11.5},
        output=args.output,
        page_slider=True,
    )

    if args.output is not None:
        print(f"Saved Qiskit example to {args.output}")


if __name__ == "__main__":
    main()
