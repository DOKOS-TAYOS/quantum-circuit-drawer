"""Qiskit marginal histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    HistogramConfig,
    HistogramDataOptions,
    HistogramSort,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)


def build_result() -> object:
    """Build a Qiskit result payload reduced to a joint marginal."""

    circuit = QuantumCircuit(5)
    circuit.ry(1.18, 0)
    circuit.ry(0.92, 2)
    circuit.h(4)
    circuit.cx(0, 1)
    circuit.cx(2, 3)
    circuit.measure_all()
    return StatevectorSampler().run([circuit], shots=512).result()


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        data=HistogramDataOptions(qubits=(4, 2, 0)),
        view=HistogramViewOptions(sort=HistogramSort.STATE),
        output=OutputOptions(output_path=output, show=show),
    )


def main() -> None:
    """Render a Qiskit joint marginal histogram demo."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_result(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-marginal to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render a Qiskit joint marginal histogram demo.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
