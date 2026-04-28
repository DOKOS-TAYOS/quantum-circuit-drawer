"""Cirq-result histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from cirq.circuits import Circuit
from cirq.devices import LineQubit
from cirq.ops import CNOT, H, measure
from cirq.sim import Simulator

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    HistogramConfig,
    HistogramStateLabelMode,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)


def build_result() -> object:
    """Build a Cirq result with two measurement registers."""

    q0, q1, q2 = LineQubit.range(3)
    circuit = Circuit(
        H(q0),
        CNOT(q0, q1),
        H(q2),
        measure(q0, q1, key="alpha"),
        measure(q2, key="beta"),
    )
    return Simulator(seed=11).run(circuit, repetitions=384)


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        view=HistogramViewOptions(state_label_mode=HistogramStateLabelMode.DECIMAL),
        output=OutputOptions(output_path=output, show=show),
    )


def main() -> None:
    """Render a histogram directly from a Cirq Result object."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_result(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-cirq-result to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render a histogram directly from a Cirq Result.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
