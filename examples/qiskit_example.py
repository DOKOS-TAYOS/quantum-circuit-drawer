"""Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from quantum_circuit_drawer import draw_quantum_circuit


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(5, "q")
    alpha = ClassicalRegister(2, "alpha")
    beta = ClassicalRegister(3, "beta")
    circuit = QuantumCircuit(quantum, alpha, beta)
    circuit.h(0)
    circuit.rx(0.37, 1)
    circuit.ry(1.11, 2)
    circuit.rzz(0.48, 3, 4)
    circuit.cx(0, 1)
    circuit.cz(1, 3)
    circuit.swap(2, 4)
    circuit.barrier(0, 1, 2)
    circuit.crz(0.72, 3, 4)
    circuit.ccx(0, 2, 3)
    circuit.swap(1, 4)
    circuit.rz(0.52, 4)
    circuit.cx(4, 2)
    circuit.barrier(2, 3, 4)
    circuit.ry(0.83, 1)
    circuit.swap(0, 3)
    circuit.cz(2, 4)
    circuit.crx(1.17, 1, 2)
    circuit.barrier()
    circuit.rx(0.66, 3)
    circuit.cx(3, 0)
    circuit.swap(1, 2)
    circuit.rzz(0.29, 0, 4)
    circuit.cy(4, 1)
    circuit.barrier()
    circuit.rx(2.21, 0)
    circuit.rz(1.43, 2)
    circuit.ry(0.91, 4)
    circuit.ccx(1, 3, 4)
    circuit.cx(4, 0)
    circuit.barrier()
    circuit.measure(4, alpha[0])
    circuit.measure(2, alpha[1])
    circuit.measure(0, beta[0])
    circuit.measure(3, beta[1])
    circuit.measure(1, beta[2])
    return circuit


def main() -> None:
    circuit = build_circuit()
    output = Path("examples/output/qiskit_circuit.png")

    draw_quantum_circuit(
        circuit,
        style={"theme": "paper", "font_size": 12.5, "show_params": True},
        output=output,
    )
    print(f"Saved Qiskit example to {output}")


if __name__ == "__main__":
    main()
