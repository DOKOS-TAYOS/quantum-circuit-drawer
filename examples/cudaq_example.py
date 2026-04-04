"""Long CUDA-Q example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

import cudaq

from quantum_circuit_drawer import draw_quantum_circuit


def parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a long CUDA-Q kernel in an interactive Matplotlib window."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    return parser.parse_args()


@cudaq.kernel
def build_kernel() -> None:
    qubits = cudaq.qvector(5)

    h(qubits[0])
    rx(0.37, qubits[1])
    ry(1.11, qubits[2])
    rz(0.48, qubits[3])
    x(qubits[4])

    x.ctrl(qubits[0], qubits[1])
    z.ctrl(qubits[1], qubits[3])
    swap(qubits[2], qubits[4])
    rz(0.72, qubits[4])
    x.ctrl(qubits[0], qubits[2], qubits[3])

    swap(qubits[1], qubits[4])
    ry(0.83, qubits[1])
    z.ctrl(qubits[2], qubits[4])
    rx(1.17, qubits[2])
    x.ctrl(qubits[3], qubits[0])

    swap(qubits[1], qubits[2])
    rz(0.29, qubits[4])
    x.ctrl(qubits[4], qubits[1])
    rx(2.21, qubits[0])
    rz(1.43, qubits[2])

    ry(0.91, qubits[4])
    z.ctrl(qubits[1], qubits[3], qubits[4])
    x.ctrl(qubits[4], qubits[0])
    swap(qubits[0], qubits[3])
    rz(0.54, qubits[3])

    mz(qubits[4])
    mz(qubits[2])
    mz(qubits[0])
    mz(qubits[3])
    mz(qubits[1])


def main() -> None:
    args = parse_args()

    draw_quantum_circuit(
        build_kernel,
        style={"font_size": 12.5, "show_params": True, "max_page_width": 11.0},
        output=args.output,
    )

    if args.output is not None:
        print(f"Saved CUDA-Q example to {args.output}")


if __name__ == "__main__":
    main()