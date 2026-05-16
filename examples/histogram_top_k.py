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

from quantum_circuit_drawer import plot_histogram  # noqa: E402

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


def main() -> None:
    """Render a histogram focused on top-k ordering and filtering."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_counts_data(),
            sort="value_desc",
            top_k=5,
            output_path=output_path,
            show=show,
            figsize=DEFAULT_HISTOGRAM_FIGSIZE,
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
