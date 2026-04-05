"""Balanced CUDA-Q example for quantum-circuit-drawer."""
# ruff: noqa: F821

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import cudaq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a balanced CUDA-Q kernel in an interactive Matplotlib window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


@cudaq.kernel
def build_kernel() -> None:
    qubits = cudaq.qvector(4)

    h(qubits[0])
    ry(0.61, qubits[1])
    rz(0.28, qubits[2])
    x(qubits[3])

    x.ctrl(qubits[0], qubits[1])
    z.ctrl(qubits[1], qubits[3])
    swap(qubits[0], qubits[2])
    ry(0.39, qubits[1])
    x.ctrl(qubits[3], qubits[0])

    mz(qubits[0])
    mz(qubits[2])
    mz(qubits[3])
    mz(qubits[1])


def main() -> None:
    args = parse_args()

    draw_quantum_circuit(
        build_kernel,
        style={"font_size": 12.0, "show_params": True, "max_page_width": 7.5},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved CUDA-Q example to {args.output}")


if __name__ == "__main__":
    main()
