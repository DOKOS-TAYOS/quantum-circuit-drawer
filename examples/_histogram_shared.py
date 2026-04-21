"""Shared helpers for histogram example entrypoints."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

try:
    from ._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import HistogramConfig, plot_histogram  # noqa: E402

DEFAULT_HISTOGRAM_FIGSIZE = (10.5, 5.6)


def demo_counts_data() -> dict[str, int]:
    """Return a shared counts payload with a full 4-bit state space."""

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


def demo_large_counts_data(*, bit_width: int = 7) -> dict[str, int]:
    """Return a larger deterministic counts payload across the full state space."""

    return {
        format(index, f"0{bit_width}b"): ((index * 17) % 41) + ((index * 5) % 13) + 3
        for index in range(2**bit_width)
    }


@dataclass(frozen=True, slots=True)
class HistogramExampleRequest:
    """Normalized render request shared by histogram example scripts."""

    output: Path | None
    show: bool
    figsize: tuple[float, float]


@dataclass(frozen=True, slots=True)
class HistogramDemoPayload:
    """One histogram demo payload plus its default config."""

    data: object
    config: HistogramConfig


HistogramDemoBuilder = Callable[[HistogramExampleRequest], HistogramDemoPayload]


def add_histogram_arguments(parser: ArgumentParser) -> None:
    """Attach the shared histogram render arguments to one parser."""

    default_figure_width, default_figure_height = DEFAULT_HISTOGRAM_FIGSIZE
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the histogram figure will also be saved.",
    )
    parser.add_argument(
        "--figsize",
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        type=float,
        default=DEFAULT_HISTOGRAM_FIGSIZE,
        help=(
            "Managed figure size in inches. "
            f"Default: {default_figure_width:g} {default_figure_height:g}."
        ),
    )
    parser.add_argument(
        "--show",
        dest="show",
        action="store_true",
        default=True,
        help="Open the Matplotlib window after rendering.",
    )
    parser.add_argument(
        "--no-show",
        dest="show",
        action="store_false",
        help="Render without opening the Matplotlib window.",
    )


def parse_histogram_example_args(*, description: str) -> HistogramExampleRequest:
    """Parse and validate the shared command-line arguments."""

    parser = ArgumentParser(description=description)
    add_histogram_arguments(parser)
    return request_from_namespace(parser.parse_args())


def request_from_namespace(args: Namespace) -> HistogramExampleRequest:
    """Normalize one parsed namespace into a histogram example request."""

    return HistogramExampleRequest(
        output=args.output,
        show=bool(args.show),
        figsize=_normalize_figsize(args.figsize),
    )


def render_histogram_example(
    payload: HistogramDemoPayload,
    *,
    request: HistogramExampleRequest,
    saved_label: str,
) -> None:
    """Plot one built histogram payload and optionally report the saved file."""

    config = replace(
        payload.config,
        output_path=request.output,
        show=request.show,
        figsize=request.figsize,
    )
    result = plot_histogram(payload.data, config=config)
    _set_histogram_figure_title(figure=result.figure, title=saved_label)
    if request.output is not None:
        print(f"Saved {saved_label} to {request.output}")


def run_histogram_example(
    builder: HistogramDemoBuilder,
    *,
    description: str,
    saved_label: str,
) -> None:
    """Parse CLI options, build the payload, and render the histogram demo."""

    request = parse_histogram_example_args(description=description)
    render_histogram_example(
        builder(request),
        request=request,
        saved_label=saved_label,
    )


def _normalize_figsize(value: object) -> tuple[float, float]:
    if not isinstance(value, tuple | list) or len(value) != 2:
        raise SystemExit("--figsize must contain width and height.")

    figure_width = float(value[0])
    figure_height = float(value[1])
    if figure_width <= 0.0 or figure_height <= 0.0:
        raise SystemExit("--figsize values must be positive.")
    return figure_width, figure_height


def _set_histogram_figure_title(*, figure: object, title: str) -> None:
    if hasattr(figure, "set_label"):
        figure.set_label(title)
    _set_histogram_window_title(figure=figure, title=title)


def _set_histogram_window_title(*, figure: object, title: str) -> None:
    canvas = getattr(figure, "canvas", None)
    manager = getattr(canvas, "manager", None)
    if manager is None or not hasattr(manager, "set_window_title"):
        return

    try:
        manager.set_window_title(title)
    except Exception:
        return
