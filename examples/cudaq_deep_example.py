"""Deep CUDA-Q example for quantum-circuit-drawer."""
# ruff: noqa: F821

from __future__ import annotations

import cudaq

try:
    from examples._shared import demo_style, run_prebuilt_example
except ImportError:
    from _shared import demo_style, run_prebuilt_example


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
    run_prebuilt_example(
        build_kernel,
        description="Render a deep CUDA-Q kernel in a compact interactive window.",
        framework=None,
        style=demo_style(max_page_width=6.0),
        page_slider=False,
        saved_label="CUDA-Q deep example",
    )


if __name__ == "__main__":
    main()
