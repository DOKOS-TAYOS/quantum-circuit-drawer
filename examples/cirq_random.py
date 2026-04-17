"""Configurable random Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from cirq.circuits import Circuit, Moment
from cirq.devices import LineQubit
from cirq.ops import CNOT, CZ, SWAP, H, X, measure, rx, ry, rz
from cirq.ops.raw_types import Operation

try:
    from examples._families import OperationSpec, build_random_columns
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import OperationSpec, build_random_columns
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> Circuit:
    """Build a deterministic random-looking Cirq circuit."""

    qubits = LineQubit.range(request.qubits)
    moments: list[Moment] = []

    for column in build_random_columns(
        qubits=request.qubits,
        columns=request.columns,
        seed=request.seed,
    ):
        moments.append(
            Moment(_build_operation(operation, qubits) for operation in column.operations)
        )

    moments.append(Moment(measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits)))
    return Circuit(*moments)


def _build_operation(operation: OperationSpec, qubits: list[LineQubit]) -> Operation:
    wire = operation.wires[0]
    if operation.name == "h":
        return H(qubits[wire])
    if operation.name == "x":
        return X(qubits[wire])
    if operation.name == "rx":
        return rx(_angle(operation))(qubits[wire])
    if operation.name == "ry":
        return ry(_angle(operation))(qubits[wire])
    if operation.name == "rz":
        return rz(_angle(operation))(qubits[wire])
    if operation.name == "cx":
        return CNOT(qubits[operation.wires[0]], qubits[operation.wires[1]])
    if operation.name == "cz":
        return CZ(qubits[operation.wires[0]], qubits[operation.wires[1]])
    return SWAP(qubits[operation.wires[0]], qubits[operation.wires[1]])


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
