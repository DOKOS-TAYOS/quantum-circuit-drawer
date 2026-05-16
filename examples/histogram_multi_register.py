"""Multi-register histogram demo for quantum-circuit-drawer."""

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
    """Return counts with two classical-register groups."""

    return {
        "00 000": 12,
        "00 101": 29,
        "01 011": 21,
        "10 001": 37,
        "10 111": 18,
        "11 010": 33,
    }


def main() -> None:
    """Render a counts histogram with several space-separated registers."""

    output_path, show = _parse_args()
    result = None
    try:
        result = plot_histogram(
            build_counts_data(),
            kind="counts",
            sort="state",
            state_label_mode="decimal",
            output_path=output_path,
            show=show,
            figsize=DEFAULT_HISTOGRAM_FIGSIZE,
        )
        if output_path is not None:
            print(f"Saved histogram-multi-register to {output_path}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> tuple[Path | None, bool]:
    parser = ArgumentParser(
        description="Render a multi-register counts histogram with decimal labels."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    args = parser.parse_args()
    return args.output, bool(args.show)


if __name__ == "__main__":
    main()
