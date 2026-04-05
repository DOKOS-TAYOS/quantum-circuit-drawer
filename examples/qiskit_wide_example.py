"""Wide Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(6, "q")
    classical = ClassicalRegister(6, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_wide_demo")

    for wire in range(6):
        circuit.h(wire)

    rounds = (
        (0.31, 0.47, 0.63, 0.82),
        (0.44, 0.58, 0.29, 0.91),
        (0.73, 0.36, 0.54, 0.67),
        (0.52, 0.78, 0.41, 0.88),
    )
    edges = ((0, 1), (1, 2), (2, 4), (4, 5), (0, 5))

    for round_index, (gamma_a, gamma_b, theta_a, theta_b) in enumerate(rounds):
        circuit.rx(theta_a, round_index % 6)
        circuit.ry(theta_b, (round_index + 2) % 6)
        circuit.rz(gamma_a, (round_index + 4) % 6)

        for left, right in edges:
            circuit.rzz(gamma_b + (0.08 * round_index), left, right)

        circuit.cx(round_index % 6, (round_index + 1) % 6)
        circuit.cz((round_index + 2) % 6, (round_index + 4) % 6)
        circuit.swap((round_index + 1) % 6, (round_index + 3) % 6)
        circuit.barrier()

    for wire in range(6):
        circuit.measure(wire, classical[wire])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a wide Qiskit circuit with a horizontal slider.",
        framework=None,
        style=demo_style(max_page_width=8.5),
        page_slider=True,
        saved_label="Qiskit wide example",
    )


if __name__ == "__main__":
    main()
