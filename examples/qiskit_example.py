"""Balanced Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(4, "q")
    classical = ClassicalRegister(4, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_balanced_demo")

    circuit.h(0)
    circuit.ry(0.61, 1)
    circuit.rz(0.28, 2)
    circuit.x(3)

    circuit.cx(0, 1)
    circuit.rzz(0.72, 1, 3)
    circuit.barrier()

    circuit.swap(0, 2)
    circuit.crz(0.44, 2, 3)
    circuit.cx(3, 0)
    circuit.ry(0.39, 1)

    circuit.measure(0, classical[0])
    circuit.measure(2, classical[1])
    circuit.measure(3, classical[2])
    circuit.measure(1, classical[3])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a balanced Qiskit circuit in an interactive Matplotlib window.",
        framework=None,
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="Qiskit example",
    )


if __name__ == "__main__":
    main()
