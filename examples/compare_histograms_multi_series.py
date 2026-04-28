"""Compare several probability distributions in one overlay histogram."""

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
from quantum_circuit_drawer.histogram import HistogramDataOptions  # noqa: E402

DEFAULT_COMPARE_FIGSIZE: tuple[float, float] = (9.2, 5.1)


def build_inputs() -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, float]]:
    """Return the four aligned distributions shown in this demo."""

    ideal = {
        "000": 0.48,
        "001": 0.01,
        "010": 0.01,
        "011": 0.0,
        "100": 0.0,
        "101": 0.01,
        "110": 0.01,
        "111": 0.48,
    }
    noisy_simulator = {
        "000": 0.42,
        "001": 0.05,
        "010": 0.03,
        "011": 0.02,
        "100": 0.02,
        "101": 0.03,
        "110": 0.05,
        "111": 0.38,
    }
    hardware_raw = {
        "000": 0.35,
        "001": 0.08,
        "010": 0.06,
        "011": 0.04,
        "100": 0.05,
        "101": 0.06,
        "110": 0.09,
        "111": 0.27,
    }
    mitigated = {
        "000": 0.44,
        "001": 0.03,
        "010": 0.02,
        "011": 0.01,
        "100": 0.01,
        "101": 0.02,
        "110": 0.04,
        "111": 0.43,
    }
    return ideal, noisy_simulator, hardware_raw, mitigated


def build_config(*, output: Path | None, show: bool) -> HistogramCompareConfig:
    """Build the compare config used by this demo."""

    return HistogramCompareConfig(
        data=HistogramDataOptions(top_k=8),
        compare=HistogramCompareOptions(
            series_labels=("Ideal", "Noisy sim", "Hardware raw", "Mitigated"),
            sort="delta_desc",
        ),
        output=OutputOptions(output_path=output, show=show, figsize=DEFAULT_COMPARE_FIGSIZE),
    )


def main() -> None:
    """Compare ideal, noisy, raw hardware, and mitigated distributions."""

    output_path, show = _parse_args()
    ideal, noisy_simulator, hardware_raw, mitigated = build_inputs()
    result = None
    try:
        result = compare_histograms(
            ideal,
            noisy_simulator,
            hardware_raw,
            mitigated,
            config=build_config(output=output_path, show=show),
        )
        if output_path is not None:
            print(f"Saved compare-histograms-multi-series to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(
        description="Compare ideal, noisy, raw hardware, and mitigated distributions."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
