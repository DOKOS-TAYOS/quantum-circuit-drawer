"""Configurable random PennyLane example for quantum-circuit-drawer."""

from __future__ import annotations

from pennylane.measurements import probs
from pennylane.ops import CNOT, CZ, RX, RY, RZ, SWAP, Hadamard, PauliX
from pennylane.tape import QuantumTape

try:
    from examples._families import OperationSpec, build_random_columns
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import OperationSpec, build_random_columns
    from _shared import ExampleRequest, run_example


def build_tape(request: ExampleRequest) -> QuantumTape:
    """Build a deterministic random-looking PennyLane tape."""

    with QuantumTape() as tape:
        for column in build_random_columns(
            qubits=request.qubits,
            columns=request.columns,
            seed=request.seed,
        ):
            for operation in column.operations:
                _apply_operation(operation)

        for wire in range(request.qubits):
            probs(wires=[wire])
    return tape


def _apply_operation(operation: OperationSpec) -> None:
    wire = operation.wires[0]
    if operation.name == "h":
        Hadamard(wires=wire)
    elif operation.name == "x":
        PauliX(wires=wire)
    elif operation.name == "rx":
        RX(_angle(operation), wires=wire)
    elif operation.name == "ry":
        RY(_angle(operation), wires=wire)
    elif operation.name == "rz":
        RZ(_angle(operation), wires=wire)
    elif operation.name == "cx":
        CNOT(wires=list(operation.wires))
    elif operation.name == "cz":
        CZ(wires=list(operation.wires))
    elif operation.name == "swap":
        SWAP(wires=list(operation.wires))


def _angle(operation: OperationSpec) -> float:
    return 0.0 if operation.angle is None else operation.angle


def main() -> None:
    run_example(
        build_tape,
        description="Render a configurable random PennyLane tape.",
        framework="pennylane",
        saved_label="PennyLane random demo",
        default_qubits=10,
        default_columns=18,
        columns_help="Random circuit columns to generate",
    )


if __name__ == "__main__":
    main()
