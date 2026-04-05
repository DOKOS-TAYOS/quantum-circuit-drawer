"""Wide CUDA-Q example for quantum-circuit-drawer."""
# ruff: noqa: F821

from __future__ import annotations

import cudaq

try:
    from examples._shared import demo_style, run_prebuilt_example
except ImportError:
    from _shared import demo_style, run_prebuilt_example


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
    run_prebuilt_example(
        build_kernel,
        description="Render a wide CUDA-Q kernel with a horizontal slider.",
        framework=None,
        style=demo_style(max_page_width=8.5),
        page_slider=True,
        saved_label="CUDA-Q wide example",
    )


if __name__ == "__main__":
    main()
