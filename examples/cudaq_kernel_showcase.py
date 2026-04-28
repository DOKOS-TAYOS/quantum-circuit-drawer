"""Showcase CUDA-Q example focused on the supported Linux/WSL subset."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import cudaq

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)


def build_parameterized_kernel(
    *, qubit_count: int, motif_count: int
) -> tuple[object, tuple[object, ...]]:
    """Build a CUDA-Q kernel that needs explicit runtime arguments."""

    kernel, size, theta = cudaq.make_kernel(int, float)
    qubits = kernel.qalloc(size)

    kernel.h(qubits[0])
    kernel.cx(qubits[0], qubits[1])
    kernel.cz(qubits[1], qubits[2])

    for step in range(motif_count):
        target = 1 + (step % max(1, qubit_count - 1))
        kernel.rz(theta, qubits[target])

    kernel.reset(qubits[1])
    kernel.mx(qubits[0])
    kernel.my(qubits[1])
    kernel.mz(qubits)
    return kernel, (qubit_count, 0.19)


def main() -> None:
    """Render a CUDA-Q kernel with runtime arguments, reset, and basis measurements."""

    args = _parse_args()
    kernel, cudaq_args = build_parameterized_kernel(
        qubit_count=args.qubits,
        motif_count=args.motifs,
    )
    result = None
    try:
        result = draw_quantum_circuit(
            kernel,
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(
                        framework="cudaq",
                        adapter_options={"cudaq_args": cudaq_args},
                    ),
                ),
                output=OutputOptions(output_path=args.output, show=args.show),
            ),
        )
        if args.output is not None:
            print(f"Saved cudaq-kernel-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a CUDA-Q kernel with runtime arguments, reset, and basis-specific measurements."
    )
    parser.add_argument("--qubits", type=int, default=3, help="Number of qubits to allocate.")
    parser.add_argument(
        "--motifs",
        type=int,
        default=4,
        help="Extra phased steps to append inside the parameterized kernel.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
