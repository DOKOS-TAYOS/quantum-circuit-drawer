"""Configurable random Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._families import OperationSpec, build_random_columns
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import OperationSpec, build_random_columns
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> QuantumCircuit:
    """Build a deterministic random-looking Qiskit circuit."""

    quantum = QuantumRegister(request.qubits, "q")
    classical = ClassicalRegister(request.qubits, "c")
    circuit = QuantumCircuit(quantum, classical, name="qiskit_random_demo")

    for column in build_random_columns(
        qubits=request.qubits,
        columns=request.columns,
        seed=request.seed,
    ):
        for operation in column.operations:
            _apply_operation(circuit, operation)

    for wire in range(request.qubits):
        circuit.measure(wire, classical[wire])
    return circuit


def _apply_operation(circuit: QuantumCircuit, operation: OperationSpec) -> None:
    wire = operation.wires[0]
    if operation.name == "h":
        circuit.h(wire)
    elif operation.name == "x":
        circuit.x(wire)
    elif operation.name == "rx":
        circuit.rx(_angle(operation), wire)
    elif operation.name == "ry":
        circuit.ry(_angle(operation), wire)
    elif operation.name == "rz":
        circuit.rz(_angle(operation), wire)
    elif operation.name == "cx":
        circuit.cx(operation.wires[0], operation.wires[1])
    elif operation.name == "cz":
        circuit.cz(operation.wires[0], operation.wires[1])
    elif operation.name == "swap":
        circuit.swap(operation.wires[0], operation.wires[1])


def _angle(operation: OperationSpec) -> float:
    return 0.0 if operation.angle is None else operation.angle


def main() -> None:
    run_example(
        build_circuit,
        description="Render a configurable random Qiskit circuit.",
        framework="qiskit",
        saved_label="Qiskit random demo",
        default_qubits=10,
        default_columns=18,
        columns_help="Random circuit columns to generate",
    )


if __name__ == "__main__":
    main()
