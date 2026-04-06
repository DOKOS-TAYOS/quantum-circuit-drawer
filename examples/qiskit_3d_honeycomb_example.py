"""Qiskit 3D honeycomb-topology example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(53, "q")
    classical = ClassicalRegister(4, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_3d_honeycomb_demo")

    for qubit_index in range(0, 53, 4):
        circuit.h(qubit_index)
    for qubit_index in range(1, 53, 6):
        circuit.rz(0.11 * (qubit_index + 1), qubit_index)

    circuit.cx(0, 13)
    circuit.cz(11, 23)
    circuit.crx(0.37, 21, 36)
    circuit.ry(0.63, 34)
    circuit.cx(44, 52)
    circuit.measure(13, classical[0])
    circuit.measure(23, classical[1])
    circuit.measure(36, classical[2])
    circuit.measure(52, classical[3])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a Qiskit circuit in the 3D honeycomb topology view.",
        framework=None,
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="Qiskit 3D honeycomb example",
        render_options={
            "view": "3d",
            "topology": "honeycomb",
            "direct": False,
            "hover": False,
        },
    )


if __name__ == "__main__":
    main()
