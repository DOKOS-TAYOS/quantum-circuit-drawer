"""Configurable random myQLM example for quantum-circuit-drawer."""

from __future__ import annotations

from qat.lang.AQASM import CNOT, CSIGN, RX, RY, RZ, SWAP, H, Program, X

try:
    from examples._families import OperationSpec, build_random_columns
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import OperationSpec, build_random_columns
    from _shared import ExampleRequest, run_example


def build_circuit(request: ExampleRequest) -> object:
    """Build a deterministic random-looking myQLM circuit."""

    program = Program()
    qbits = program.qalloc(request.qubits)
    cbits = program.calloc(request.qubits)

    for column in build_random_columns(
        qubits=request.qubits,
        columns=request.columns,
        seed=request.seed,
    ):
        for operation in column.operations:
            _apply_operation(qbits, operation)

    program.measure(list(qbits), list(cbits))
    return program.to_circ()


def _apply_operation(qbits: object, operation: OperationSpec) -> None:
    wire = operation.wires[0]
    if operation.name == "h":
        H(qbits[wire])
    elif operation.name == "x":
        X(qbits[wire])
    elif operation.name == "rx":
        RX(_angle(operation))(qbits[wire])
    elif operation.name == "ry":
        RY(_angle(operation))(qbits[wire])
    elif operation.name == "rz":
        RZ(_angle(operation))(qbits[wire])
    elif operation.name == "cx":
        CNOT(qbits[operation.wires[0]], qbits[operation.wires[1]])
    elif operation.name == "cz":
        CSIGN(qbits[operation.wires[0]], qbits[operation.wires[1]])
    elif operation.name == "swap":
        SWAP(qbits[operation.wires[0]], qbits[operation.wires[1]])


def _angle(operation: OperationSpec) -> float:
    return 0.0 if operation.angle is None else operation.angle


def main() -> None:
    run_example(
        build_circuit,
        description="Render a configurable random myQLM circuit.",
        framework="myqlm",
        saved_label="myQLM random demo",
        default_qubits=10,
        default_columns=18,
        columns_help="Random circuit columns to generate",
    )


if __name__ == "__main__":
    main()
