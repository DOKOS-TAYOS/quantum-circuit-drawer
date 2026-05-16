"""Uniform-reference histogram demo for quantum-circuit-drawer."""

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
    HistogramDrawStyle,
    plot_histogram,
)

DEFAULT_HISTOGRAM_FIGSIZE: tuple[float, float] = (10.8, 6.1)


def build_counts_data() -> dict[str, int]:
    """Return a full 4-bit counts payload with varied weights."""

    return {
        "0000": 41,
        "0001": 9,
        "0010": 18,
        "0011": 67,
        "0100": 12,
        "0101": 53,
        "0110": 24,
        "0111": 31,
        "1000": 88,
        "1001": 16,
        "1010": 74,
        "1011": 11,
        "1100": 58,
        "1101": 21,
        "1110": 44,
        "1111": 95,
    }


def build_config() -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        appearance=HistogramAppearanceOptions(
            draw_style=HistogramDrawStyle.OUTLINE,
            show_uniform_reference=True,
        ),
    )


def main() -> None:
    """Render a counts histogram with a uniform reference guide."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_counts_data(),
            kind="counts",
            output_path=output_path,
            show=show,
            figsize=DEFAULT_HISTOGRAM_FIGSIZE,
            config=build_config(),
        )
        if output_path is not None:
            print(f"Saved histogram-uniform-reference to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(
        description="Render a counts histogram with the uniform reference line."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
