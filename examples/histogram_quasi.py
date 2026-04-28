"""Quasi-probability histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

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
    HistogramDataOptions,
    HistogramDrawStyle,
    HistogramKind,
    OutputOptions,
    plot_histogram,
)

DEFAULT_HISTOGRAM_FIGSIZE: tuple[float, float] = (9.0, 5.1)


def build_quasi_distribution() -> dict[str, float]:
    """Return a quasi-probability distribution with negative bars."""

    return {
        "0000": 0.21,
        "0001": 0.08,
        "0011": -0.04,
        "0101": 0.15,
        "0110": 0.12,
        "1001": -0.03,
        "1100": 0.19,
        "1111": 0.32,
    }


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        data=HistogramDataOptions(kind=HistogramKind.QUASI),
        appearance=HistogramAppearanceOptions(
            theme="paper",
            draw_style=HistogramDrawStyle.SOFT,
        ),
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_HISTOGRAM_FIGSIZE),
    )


def main() -> None:
    """Render a quasi-probability histogram with negative values."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_quasi_distribution(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-quasi to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render a quasi-probability histogram with negative bars.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
