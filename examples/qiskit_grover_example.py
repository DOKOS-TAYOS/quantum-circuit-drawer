"""Grover search example in Qiskit for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


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
    run_example(
        build_circuit,
        description="Render a small Grover search circuit built with Qiskit.",
        framework=None,
        style=demo_style(max_page_width=6.5),
        page_slider=False,
        saved_label="Qiskit Grover example",
    )


if __name__ == "__main__":
    main()
