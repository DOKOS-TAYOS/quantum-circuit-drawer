"""Configurable random CUDA-Q example for quantum-circuit-drawer."""

from __future__ import annotations

import cudaq

try:
    from examples._families import OperationSpec, build_random_columns
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _families import OperationSpec, build_random_columns
    from _shared import ExampleRequest, run_example


def build_kernel(request: ExampleRequest) -> object:
    """Build a deterministic random-looking CUDA-Q kernel."""

    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(request.qubits)

    for column in build_random_columns(
        qubits=request.qubits,
        columns=request.columns,
        seed=request.seed,
    ):
        for operation in column.operations:
            _apply_operation(kernel, qubits, operation)

    kernel.mz(qubits)
    return kernel


def _apply_operation(kernel: object, qubits: object, operation: OperationSpec) -> None:
    wire = operation.wires[0]
    if operation.name == "h":
        kernel.h(qubits[wire])
    elif operation.name == "x":
        kernel.x(qubits[wire])
    elif operation.name == "rx":
        kernel.rx(_angle(operation), qubits[wire])
    elif operation.name == "ry":
        kernel.ry(_angle(operation), qubits[wire])
    elif operation.name == "rz":
        kernel.rz(_angle(operation), qubits[wire])
    elif operation.name == "cx":
        kernel.cx(qubits[operation.wires[0]], qubits[operation.wires[1]])
    elif operation.name == "cz":
        kernel.cz(qubits[operation.wires[0]], qubits[operation.wires[1]])
    elif operation.name == "swap":
        kernel.swap(qubits[operation.wires[0]], qubits[operation.wires[1]])


def _angle(operation: OperationSpec) -> float:
    return 0.0 if operation.angle is None else operation.angle


def main() -> None:
    run_example(
        build_kernel,
        description="Render a configurable random CUDA-Q kernel.",
        framework="cudaq",
        saved_label="CUDA-Q random demo",
        default_qubits=10,
        default_columns=18,
        columns_help="Random circuit columns to generate",
    )


if __name__ == "__main__":
    main()
