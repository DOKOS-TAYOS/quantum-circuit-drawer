"""Deep Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._shared import demo_style, run_example
except ImportError:
    from _shared import demo_style, run_example


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
    run_example(
        build_circuit,
        description="Render a deep Qiskit circuit in a compact interactive window.",
        framework=None,
        style=demo_style(max_page_width=6.0),
        page_slider=False,
        saved_label="Qiskit deep example",
    )


if __name__ == "__main__":
    main()
