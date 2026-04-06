"""Qiskit 3D grid-topology example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(9, "q")
    classical = ClassicalRegister(3, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_3d_grid_demo")

    for qubit_index in range(9):
        if qubit_index % 2 == 0:
            circuit.h(qubit_index)
        else:
            circuit.rz(0.17 * (qubit_index + 1), qubit_index)

    circuit.cx(0, 8)
    circuit.cz(2, 6)
    circuit.crx(0.44, 1, 4)
    circuit.ry(0.71, 7)
    circuit.measure(8, classical[0])
    circuit.measure(4, classical[1])
    circuit.measure(0, classical[2])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a Qiskit circuit in the 3D grid topology view.",
        framework=None,
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="Qiskit 3D grid example",
        render_options={"view": "3d", "topology": "grid", "direct": False, "hover": True},
    )


if __name__ == "__main__":
    main()
