"""Histogram demo focused on selecting one result from a tuple payload."""

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


def build_payload() -> tuple[dict[str, int], ...]:
    """Return a tuple of histogram payloads like a multi-result workflow."""

    return (
        {"00": 41, "11": 39},
        {"00": 12, "01": 18, "10": 11, "11": 23},
        {"00": 5, "01": 7, "10": 8, "11": 10},
    )


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        data=HistogramDataOptions(result_index=1),
        view=HistogramViewOptions(sort="value_desc"),
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_HISTOGRAM_FIGSIZE),
    )


def main() -> None:
    """Render one selected histogram from a tuple of several results."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_payload(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-result-index to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render one selected histogram from a tuple payload.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
