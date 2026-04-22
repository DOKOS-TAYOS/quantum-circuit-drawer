"""Showcase CUDA-Q example focused on the supported closed-kernel subset."""

from __future__ import annotations

import cudaq

try:
    from examples._shared import ExampleRequest, run_example
except ImportError:
    from _shared import ExampleRequest, run_example


def build_kernel(request: ExampleRequest) -> object:
    """Build a CUDA-Q kernel that highlights resets and basis-specific measurements."""

    qubit_count = max(3, request.qubits)
    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(qubit_count)

    kernel.h(qubits[0])
    kernel.cx(qubits[0], qubits[1])
    kernel.cz(qubits[1], qubits[2])

    for step in range(_motif_count(request)):
        target = 1 + (step % max(1, qubit_count - 1))
        kernel.rz(0.19 * float(step + 1), qubits[target])

    kernel.reset(qubits[1])
    kernel.mx(qubits[0])
    kernel.my(qubits[1])
    kernel.mz(qubits[2])
    return kernel


def _motif_count(request: ExampleRequest) -> int:
    return max(2, min(request.columns, 6))


def main() -> None:
    run_example(
        build_kernel,
        description="Render a CUDA-Q showcase with a closed kernel, reset, and basis measurements.",
        framework="cudaq",
        saved_label="CUDA-Q kernel showcase",
        default_qubits=3,
        default_columns=4,
        columns_help="Extra phased steps to append inside the closed CUDA-Q kernel",
    )


if __name__ == "__main__":
    main()
