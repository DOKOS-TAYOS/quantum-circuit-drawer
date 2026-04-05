"""Wide CUDA-Q example for quantum-circuit-drawer."""
# ruff: noqa: F821

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import cudaq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Render a wide CUDA-Q kernel with a horizontal slider.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


@cudaq.kernel
def build_kernel() -> None:
    qubits = cudaq.qvector(6)

    h(qubits[0])
    h(qubits[1])
    h(qubits[2])
    h(qubits[3])
    h(qubits[4])
    h(qubits[5])

    rx(0.31, qubits[0])
    ry(0.47, qubits[2])
    rz(0.63, qubits[4])
    x.ctrl(qubits[0], qubits[1])
    swap(qubits[2], qubits[4])
    z.ctrl(qubits[4], qubits[5])

    rx(0.44, qubits[1])
    ry(0.58, qubits[3])
    rz(0.29, qubits[5])
    x.ctrl(qubits[1], qubits[2])
    swap(qubits[0], qubits[3])
    z.ctrl(qubits[2], qubits[4])

    rx(0.73, qubits[2])
    ry(0.36, qubits[4])
    rz(0.54, qubits[0])
    x.ctrl(qubits[3], qubits[5])
    swap(qubits[1], qubits[4])
    z.ctrl(qubits[0], qubits[2], qubits[5])

    rx(0.52, qubits[5])
    ry(0.78, qubits[1])
    rz(0.41, qubits[3])
    x.ctrl(qubits[5], qubits[0])
    swap(qubits[2], qubits[3])
    z.ctrl(qubits[1], qubits[4])

    mz(qubits[0])
    mz(qubits[1])
    mz(qubits[2])
    mz(qubits[3])
    mz(qubits[4])
    mz(qubits[5])


def main() -> None:
    args = parse_args()

    draw_quantum_circuit(
        build_kernel,
        style={"font_size": 12.0, "show_params": True, "max_page_width": 8.5},
        output=args.output,
        page_slider=True,
    )

    if args.output is not None:
        print(f"Saved CUDA-Q wide example to {args.output}")


if __name__ == "__main__":
    main()
