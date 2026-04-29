"""Histogram demo focused on top-k ordering and filtering."""

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
    HistogramConfig,
    HistogramDataOptions,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)

DEFAULT_HISTOGRAM_FIGSIZE: tuple[float, float] = (10.8, 6.1)


def build_counts_data() -> dict[str, int]:
    """Return counts that make top-k filtering easy to see."""

    return {
        "0000": 14,
        "0001": 5,
        "0010": 21,
        "0011": 7,
        "0100": 17,
        "0101": 3,
        "0110": 26,
        "0111": 11,
        "1000": 31,
        "1001": 9,
        "1010": 28,
        "1011": 4,
        "1100": 22,
        "1101": 8,
        "1110": 18,
        "1111": 35,
    }


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        data=HistogramDataOptions(top_k=5),
        view=HistogramViewOptions(sort="value_desc"),
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_HISTOGRAM_FIGSIZE),
    )


def main() -> None:
    """Render a histogram focused on top-k ordering and filtering."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_counts_data(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-top-k to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(
        description="Render a histogram focused on top-k ordering and filtering."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
