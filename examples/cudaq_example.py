"""Balanced CUDA-Q example for quantum-circuit-drawer."""
# ruff: noqa: F821

from __future__ import annotations

import cudaq

try:
    from examples._shared import demo_style, run_prebuilt_example
except ImportError:
    from _shared import demo_style, run_prebuilt_example


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
    run_prebuilt_example(
        build_kernel,
        description="Render a balanced CUDA-Q kernel in an interactive Matplotlib window.",
        framework=None,
        style=demo_style(max_page_width=7.5),
        page_slider=False,
        saved_label="CUDA-Q example",
    )


if __name__ == "__main__":
    main()
