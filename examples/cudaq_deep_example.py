"""Deep CUDA-Q example for quantum-circuit-drawer."""
# ruff: noqa: F821

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import cudaq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a deep CUDA-Q kernel in a compact interactive window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


@cudaq.kernel
def build_kernel() -> None:
    qubits = cudaq.qvector(3)

    rx(0.22, qubits[0])
    ry(0.35, qubits[1])
    rz(0.19, qubits[2])
    x.ctrl(qubits[0], qubits[1])
    swap(qubits[0], qubits[2])

    rx(0.33, qubits[0])
    ry(0.42, qubits[1])
    rz(0.24, qubits[2])
    z.ctrl(qubits[2], qubits[1])

    rx(0.44, qubits[0])
    ry(0.49, qubits[1])
    rz(0.29, qubits[2])
    x.ctrl(qubits[1], qubits[2])
    swap(qubits[0], qubits[1])

    rx(0.55, qubits[0])
    ry(0.56, qubits[1])
    rz(0.34, qubits[2])
    z.ctrl(qubits[0], qubits[2])

    rx(0.66, qubits[0])
    ry(0.63, qubits[1])
    rz(0.39, qubits[2])
    x.ctrl(qubits[2], qubits[0])

    mz(qubits[0])
    mz(qubits[1])
    mz(qubits[2])


def main() -> None:
    args = parse_args()

    draw_quantum_circuit(
        build_kernel,
        style={"font_size": 12.0, "show_params": True, "max_page_width": 6.0},
        output=args.output,
        page_slider=False,
    )

    if args.output is not None:
        print(f"Saved CUDA-Q deep example to {args.output}")


if __name__ == "__main__":
    main()
