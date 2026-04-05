"""QAOA example in Qiskit for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(4, "q")
    classical = ClassicalRegister(4, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_qaoa_demo")

    edges = ((0, 1), (1, 2), (2, 3), (3, 0))
    gammas = (0.45, 0.73)
    betas = (0.31, 0.52)

    for wire in range(4):
        circuit.h(wire)

    for gamma, beta in zip(gammas, betas, strict=True):
        for left, right in edges:
            circuit.rzz(gamma, left, right)
        for wire in range(4):
            circuit.rx(2.0 * beta, wire)

    for wire in range(4):
        circuit.measure(wire, classical[wire])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a small QAOA MaxCut circuit built with Qiskit.",
        framework=None,
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="Qiskit QAOA example",
    )


if __name__ == "__main__":
    main()
