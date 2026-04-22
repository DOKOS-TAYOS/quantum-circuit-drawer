"""Showcase CUDA-Q example focused on the supported closed-kernel subset."""

from __future__ import annotations

import cudaq

try:
    from examples._shared import ExampleRequest, build_draw_config, parse_example_args
except ImportError:
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import draw_quantum_circuit


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
    request = parse_example_args(
        description="Render a CUDA-Q showcase for the supported closed-kernel subset with reset and basis measurements.",
        default_qubits=3,
        default_columns=4,
        columns_help="Extra phased steps to append inside the closed CUDA-Q kernel",
    )
    draw_quantum_circuit(
        build_kernel(request),
        config=build_draw_config(request, framework="cudaq"),
    )
    if request.output is not None:
        print(f"Saved cudaq-kernel-showcase to {request.output}")


if __name__ == "__main__":
    main()
