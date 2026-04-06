"""Qiskit 3D line-topology example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


def build_circuit() -> QuantumCircuit:
    quantum = QuantumRegister(5, "q")
    classical = ClassicalRegister(2, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_3d_line_demo")

    circuit.h(0)
    circuit.ry(0.43, 2)
    circuit.cx(0, 4)
    circuit.crz(0.58, 1, 3)
    circuit.swap(2, 4)
    circuit.measure(4, classical[0])
    circuit.measure(1, classical[1])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a Qiskit circuit in the 3D line topology view.",
        framework=None,
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="Qiskit 3D line example",
        render_options={"view": "3d", "topology": "line", "direct": True, "hover": False},
    )


if __name__ == "__main__":
    main()
