"""CUDA-Q-sample histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import cudaq

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import plot_histogram  # noqa: E402


def build_sample_result() -> object:
    """Build a CUDA-Q sample result from a small kernel."""

    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(3)
    kernel.h(qubits[0])
    kernel.cx(qubits[0], qubits[1])
    kernel.ry(0.41, qubits[2])
    kernel.mz(qubits)
    return cudaq.sample(kernel, shots_count=512)


def main() -> None:
    """Render a histogram directly from a CUDA-Q sample result."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_sample_result(),
            sort="value_desc",
            output_path=output_path,
            show=show,
        )
        if output_path is not None:
            print(f"Saved histogram-cudaq-sample to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render a histogram directly from a CUDA-Q sample result.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
