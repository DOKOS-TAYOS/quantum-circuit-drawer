"""Configurable random Qiskit example for quantum-circuit-drawer."""

from __future__ import annotations

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

try:
    from examples._families import OperationSpec, build_random_columns
    from examples._shared import ExampleRequest, build_draw_config, parse_example_args
except ImportError:
    from _families import OperationSpec, build_random_columns
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import draw_quantum_circuit


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
    request = parse_example_args(
        description="Render a configurable random Qiskit circuit.",
        default_qubits=10,
        default_columns=18,
        columns_help="Random circuit columns to generate",
    )
    draw_quantum_circuit(
        build_circuit(request),
        config=build_draw_config(request, framework="qiskit"),
    )
    if request.output is not None:
        print(f"Saved qiskit-random to {request.output}")


if __name__ == "__main__":
    main()
