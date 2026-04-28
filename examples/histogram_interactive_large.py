"""Large histogram demo for quantum-circuit-drawer with auto interactive controls."""

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
    HistogramKind,
    HistogramSort,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)

DEFAULT_HISTOGRAM_FIGSIZE: tuple[float, float] = (9.6, 5.2)


def build_counts_data(*, bit_width: int = 7) -> dict[str, int]:
    """Return a larger deterministic counts payload across the full state space."""

    return {
        format(index, f"0{bit_width}b"): ((index * 17) % 41) + ((index * 5) % 13) + 3
        for index in range(2**bit_width)
    }


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        data=HistogramDataOptions(kind=HistogramKind.COUNTS),
        view=HistogramViewOptions(sort=HistogramSort.STATE),
        appearance=HistogramAppearanceOptions(show_uniform_reference=True),
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_HISTOGRAM_FIGSIZE),
    )


def main() -> None:
    """Render a 7-bit histogram with enough bins to trigger managed controls."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_counts_data(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-interactive-large to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(
        description="Render a large histogram that is easy to explore interactively."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
