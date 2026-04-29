"""Compare ideal and sampled histogram workflows with the public compare API."""

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
    HistogramCompareConfig,
    HistogramCompareOptions,
    OutputOptions,
    compare_histograms,
)

DEFAULT_COMPARE_FIGSIZE: tuple[float, float] = (11.0, 6.1)


def build_inputs() -> tuple[dict[str, float], dict[str, int]]:
    """Return the ideal and sampled distributions shown in this demo."""

    ideal = {
        "000": 0.125,
        "001": 0.125,
        "010": 0.125,
        "011": 0.125,
        "100": 0.125,
        "101": 0.125,
        "110": 0.125,
        "111": 0.125,
    }
    sampled = {
        "000": 17,
        "001": 13,
        "010": 9,
        "011": 18,
        "100": 12,
        "101": 10,
        "110": 15,
        "111": 14,
    }
    return ideal, sampled


def build_config(*, output: Path | None, show: bool) -> HistogramCompareConfig:
    """Build the compare config used by this demo."""

    return HistogramCompareConfig(
        compare=HistogramCompareOptions(
            left_label="Ideal",
            right_label="Sampled",
            sort="delta_desc",
        ),
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_COMPARE_FIGSIZE),
    )


def main() -> None:
    """Compare an ideal distribution against sampled counts."""

    output_path, show = _parse_args()
    ideal, sampled = build_inputs()
    result = None
    try:
        result = compare_histograms(
            ideal,
            sampled,
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved compare-histograms-ideal-vs-sampled to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Compare an ideal distribution against sampled counts.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
