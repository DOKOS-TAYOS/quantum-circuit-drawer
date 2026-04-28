"""myQLM-result histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path

from qat.core import Result

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    HistogramConfig,
    HistogramSort,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)


def build_result() -> Result:
    """Build a myQLM Result with raw_data samples."""

    result = Result(nbqbits=4)
    result.add_sample(state=0b0000, probability=93)
    result.add_sample(state=0b0011, probability=128)
    result.add_sample(state=0b1010, probability=77)
    result.add_sample(state=0b1111, probability=214)
    return result


def build_config(*, output: Path | None, show: bool) -> HistogramConfig:
    """Build the histogram config used by this demo."""

    return HistogramConfig(
        view=HistogramViewOptions(sort=HistogramSort.VALUE_DESC),
        output=OutputOptions(output_path=output, show=show),
    )


def main() -> None:
    """Render a histogram directly from a myQLM Result.raw_data payload."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_result(),
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved histogram-myqlm-result to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(description="Render a histogram directly from a myQLM result object.")
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
