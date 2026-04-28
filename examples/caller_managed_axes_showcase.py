"""Compose circuit, histogram, and comparison plots on caller-managed axes."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt

try:
    from examples._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitAppearanceOptions,
    CircuitBuilder,
    CircuitCompareConfig,
    CircuitCompareOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramMode,
    HistogramViewOptions,
    OutputOptions,
    compare_circuits,
    draw_quantum_circuit,
    plot_histogram,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


@dataclass(frozen=True, slots=True)
class DashboardLayout:
    """Axes used by the caller-managed dashboard."""

    circuit_axes: Axes
    histogram_axes: Axes
    compare_axes: tuple[Axes, Axes]
    summary_axes: Axes


def build_left_circuit() -> object:
    """Build the left circuit in the caller-managed axes dashboard."""

    return (
        CircuitBuilder(4, 4, name="caller_axes_left")
        .h(0)
        .cx(0, 1)
        .ry(0.35, 2)
        .cz(2, 3)
        .barrier()
        .measure_all()
        .build()
    )


def build_right_circuit() -> object:
    """Build the comparison circuit with a small structural change."""

    return (
        CircuitBuilder(4, 4, name="caller_axes_right")
        .h(0)
        .cx(0, 1)
        .ry(0.72, 2)
        .swap(2, 3)
        .cz(1, 3)
        .measure_all()
        .build()
    )


def demo_counts() -> dict[str, int]:
    """Return counts for the histogram panel."""

    return {
        "0000": 11,
        "0001": 7,
        "0010": 23,
        "0011": 41,
        "0100": 18,
        "0101": 5,
        "0110": 29,
        "0111": 13,
    }


def main() -> None:
    """Run the caller-managed axes showcase."""

    output_path, show = _parse_args()
    figure, layout = create_dashboard_layout()
    circuit = build_left_circuit()
    comparison_circuit = build_right_circuit()

    draw_quantum_circuit(
        circuit,
        ax=layout.circuit_axes,
        config=DrawConfig(
            side=DrawSideConfig(
                render=CircuitRenderOptions(mode=DrawMode.FULL, framework="ir"),
                appearance=CircuitAppearanceOptions(preset="paper"),
            ),
            output=OutputOptions(show=False),
        ),
    )
    plot_histogram(
        demo_counts(),
        ax=layout.histogram_axes,
        config=build_histogram_config(),
    )
    compare_circuits(
        circuit,
        comparison_circuit,
        axes=layout.compare_axes,
        summary_ax=layout.summary_axes,
        config=build_compare_config(),
    )
    figure.suptitle("caller-managed axes")
    if output_path is not None:
        figure.savefig(output_path, bbox_inches="tight")
        print(f"Saved caller-managed-axes-showcase to {output_path}")
    if show:
        plt.show()
    plt.close(figure)


def create_dashboard_layout() -> tuple[Figure, DashboardLayout]:
    """Create a five-panel Matplotlib dashboard layout."""

    figure = plt.figure(figsize=(10.2, 6.2), constrained_layout=True)
    grid = figure.add_gridspec(
        3,
        2,
        height_ratios=(1.0, 1.0, 0.72),
        hspace=0.24,
        wspace=0.12,
    )
    layout = DashboardLayout(
        circuit_axes=figure.add_subplot(grid[0, 0]),
        histogram_axes=figure.add_subplot(grid[0, 1]),
        compare_axes=(
            figure.add_subplot(grid[1, 0]),
            figure.add_subplot(grid[1, 1]),
        ),
        summary_axes=figure.add_subplot(grid[2, :]),
    )
    return figure, layout


def build_histogram_config() -> HistogramConfig:
    """Build the light-theme histogram config used by the dashboard."""

    return HistogramConfig(
        data=HistogramDataOptions(top_k=6),
        view=HistogramViewOptions(mode=HistogramMode.STATIC, sort="value_desc"),
        appearance=HistogramAppearanceOptions(theme="light"),
        output=OutputOptions(show=False),
    )


def build_compare_config() -> CircuitCompareConfig:
    """Build the caller-owned axes comparison config."""

    return CircuitCompareConfig(
        shared=DrawSideConfig(
            render=CircuitRenderOptions(mode=DrawMode.FULL, framework="ir"),
            appearance=CircuitAppearanceOptions(preset="notebook"),
        ),
        compare=CircuitCompareOptions(
            left_title="Reference",
            right_title="Variant",
            show_summary=True,
        ),
        output=OutputOptions(show=False),
    )


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render a mixed dashboard with caller-managed axes.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
