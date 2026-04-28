"""PennyLane-probability histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

import pennylane as qml

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramSort,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)


def build_probabilities() -> object:
    """Return a PennyLane probability vector from a small circuit."""

    device = qml.device("default.qubit", wires=4)

    @qml.qnode(device)
    def probability_demo() -> object:
        qml.Hadamard(wires=0)
        qml.CNOT(wires=[0, 1])
        qml.RY(0.43, wires=2)
        qml.CNOT(wires=[2, 3])
        return qml.probs(wires=[0, 1, 2, 3])

    return probability_demo()


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        view=HistogramViewOptions(sort=HistogramSort.VALUE_DESC),
        appearance=HistogramAppearanceOptions(show_uniform_reference=True),
        output=OutputOptions(output_path=output, show=show),
    )


def main() -> None:
    """Render a histogram from a PennyLane qml.probs() vector."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_probabilities(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-pennylane-probs to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render a histogram from a PennyLane probability vector.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
