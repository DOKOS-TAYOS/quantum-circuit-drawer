"""Configurable QAOA Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._families import build_cycle_edges, build_qaoa_layers
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import build_cycle_edges, build_qaoa_layers
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> QuantumCircuit:
    """Build a ring-QAOA Qiskit circuit."""

    quantum = QuantumRegister(request.qubits, "q")
    classical = ClassicalRegister(request.qubits, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_qaoa_demo")

    for wire in range(request.qubits):
        circuit.h(wire)

    edges = build_cycle_edges(request.qubits)
    for layer in build_qaoa_layers(layers=request.columns):
        for left, right in edges:
            circuit.rzz(layer.gamma, left, right)
        for wire in range(request.qubits):
            circuit.rx(2.0 * layer.beta, wire)

    for wire in range(request.qubits):
        circuit.measure(wire, classical[wire])
    return circuit


def main() -> None:
    run_example(
        build_circuit,
        description="Render a configurable QAOA MaxCut circuit in Qiskit.",
        framework="qiskit",
        saved_label="Qiskit QAOA demo",
        default_qubits=8,
        default_columns=6,
        columns_help="QAOA layers to generate",
    )


if __name__ == "__main__":
    main()
