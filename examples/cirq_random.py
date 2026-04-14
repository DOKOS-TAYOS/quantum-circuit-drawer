"""Configurable random Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

import cirq

try:
    from examples._families import OperationSpec, build_random_columns
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import OperationSpec, build_random_columns
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> cirq.Circuit:
    """Build a deterministic random-looking Cirq circuit."""

    qubits = cirq.LineQubit.range(request.qubits)
    moments: list[cirq.Moment] = []

    for column in build_random_columns(
        qubits=request.qubits,
        columns=request.columns,
        seed=request.seed,
    ):
        moments.append(
            cirq.Moment(_build_operation(operation, qubits) for operation in column.operations)
        )

    moments.append(
        cirq.Moment(cirq.measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits))
    )
    return cirq.Circuit(*moments)


def _build_operation(operation: OperationSpec, qubits: list[cirq.LineQubit]) -> cirq.Operation:
    wire = operation.wires[0]
    if operation.name == "h":
        return cirq.H(qubits[wire])
    if operation.name == "x":
        return cirq.X(qubits[wire])
    if operation.name == "rx":
        return cirq.rx(_angle(operation))(qubits[wire])
    if operation.name == "ry":
        return cirq.ry(_angle(operation))(qubits[wire])
    if operation.name == "rz":
        return cirq.rz(_angle(operation))(qubits[wire])
    if operation.name == "cx":
        return cirq.CNOT(qubits[operation.wires[0]], qubits[operation.wires[1]])
    if operation.name == "cz":
        return cirq.CZ(qubits[operation.wires[0]], qubits[operation.wires[1]])
    return cirq.SWAP(qubits[operation.wires[0]], qubits[operation.wires[1]])


def _angle(operation: OperationSpec) -> float:
    return 0.0 if operation.angle is None else operation.angle


def main() -> None:
    run_example(
        build_circuit,
        description="Render a configurable random Cirq circuit.",
        framework="cirq",
        saved_label="Cirq random demo",
        default_qubits=10,
        default_columns=18,
        columns_help="Random circuit columns to generate",
    )


if __name__ == "__main__":
    main()
