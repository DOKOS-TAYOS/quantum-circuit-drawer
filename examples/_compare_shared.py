"""Shared helpers for compare example entrypoints."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal, cast

try:
    from ._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitCompareConfig,
    compare_circuits,
    compare_histograms,
)
from quantum_circuit_drawer.histogram import HistogramCompareConfig  # noqa: E402

CompareKind = Literal["circuits", "histograms"]
HistogramCompareSortName = Literal["state", "state_desc", "delta_desc"]
DEFAULT_COMPARE_FIGSIZE = (11.0, 5.6)


@dataclass(frozen=True, slots=True)
class CompareExampleRequest:
    """Normalized render request shared by compare example scripts."""

    output: Path | None
    show: bool
    figsize: tuple[float, float]
    left_label: str | None = None
    right_label: str | None = None
    highlight_differences: bool | None = None
    show_summary: bool | None = None
    sort: HistogramCompareSortName | None = None
    top_k: int | None = None


@dataclass(frozen=True, slots=True)
class CompareDemoPayload:
    """Payload for one compare demo plus its default config."""

    compare_kind: CompareKind
    left_data: object
    right_data: object
    config: CircuitCompareConfig | HistogramCompareConfig
    left_config: object | None = None
    right_config: object | None = None


CompareDemoBuilder = Callable[[CompareExampleRequest], CompareDemoPayload]


def add_compare_arguments(parser: ArgumentParser) -> None:
    """Attach the shared compare render arguments to one parser."""

    default_figure_width, default_figure_height = DEFAULT_COMPARE_FIGSIZE
    parser.add_argument("--left-label", help="Optional label for the left-hand side.")
    parser.add_argument("--right-label", help="Optional label for the right-hand side.")
    parser.add_argument(
        "--highlight-differences",
        dest="highlight_differences",
        action="store_true",
        default=None,
        help="Highlight circuit differences when the compare demo supports it.",
    )
    parser.add_argument(
        "--no-highlight-differences",
        dest="highlight_differences",
        action="store_false",
        help="Disable difference highlighting for circuit-compare demos.",
    )
    parser.add_argument(
        "--show-summary",
        dest="show_summary",
        action="store_true",
        default=None,
        help="Show the comparison summary panel when the compare demo supports it.",
    )
    parser.add_argument(
        "--no-show-summary",
        dest="show_summary",
        action="store_false",
        help="Hide the comparison summary panel for circuit-compare demos.",
    )
    parser.add_argument(
        "--sort",
        choices=("state", "state_desc", "delta_desc"),
        help="Optional ordering override for histogram-compare demos.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="Optional top-k override for histogram-compare demos.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the compare figure will also be saved.",
    )
    parser.add_argument(
        "--figsize",
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        type=float,
        default=DEFAULT_COMPARE_FIGSIZE,
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


def parse_compare_example_args(*, description: str) -> CompareExampleRequest:
    """Parse and validate the shared command-line arguments."""

    parser = ArgumentParser(description=description)
    add_compare_arguments(parser)
    return request_from_namespace(parser.parse_args())


def request_from_namespace(args: Namespace) -> CompareExampleRequest:
    """Normalize one parsed namespace into a compare request."""

    return CompareExampleRequest(
        output=getattr(args, "output", None),
        show=bool(getattr(args, "show", True)),
        figsize=_normalize_figsize(getattr(args, "figsize", DEFAULT_COMPARE_FIGSIZE)),
        left_label=_optional_str(getattr(args, "left_label", None)),
        right_label=_optional_str(getattr(args, "right_label", None)),
        highlight_differences=_optional_bool(getattr(args, "highlight_differences", None)),
        show_summary=_optional_bool(getattr(args, "show_summary", None)),
        sort=_optional_sort(getattr(args, "sort", None)),
        top_k=_optional_top_k(getattr(args, "top_k", None)),
    )


def render_compare_example(
    payload: CompareDemoPayload,
    *,
    request: CompareExampleRequest,
    saved_label: str,
) -> None:
    """Render one compare payload and optionally report the saved file."""

    if payload.compare_kind == "circuits":
        config = _merge_circuit_compare_config(
            cast(CircuitCompareConfig, payload.config),
            request=request,
        )
        result = compare_circuits(
            payload.left_data,
            payload.right_data,
            left_config=payload.left_config,
            right_config=payload.right_config,
            config=config,
        )
    else:
        config = _merge_histogram_compare_config(
            cast(HistogramCompareConfig, payload.config),
            request=request,
        )
        result = compare_histograms(
            payload.left_data,
            payload.right_data,
            config=config,
        )
    _set_compare_figure_title(figure=result.figure, title=saved_label)
    if request.output is not None:
        print(f"Saved {saved_label} to {request.output}")


def run_compare_example(
    builder: CompareDemoBuilder,
    *,
    description: str,
    saved_label: str,
) -> None:
    """Parse CLI options, build the payload, and render the compare demo."""

    request = parse_compare_example_args(description=description)
    render_compare_example(
        builder(request),
        request=request,
        saved_label=saved_label,
    )


def _merge_circuit_compare_config(
    config: CircuitCompareConfig,
    *,
    request: CompareExampleRequest,
) -> CircuitCompareConfig:
    return replace(
        config,
        left_title=request.left_label or config.left_title,
        right_title=request.right_label or config.right_title,
        highlight_differences=(
            config.highlight_differences
            if request.highlight_differences is None
            else request.highlight_differences
        ),
        show_summary=config.show_summary if request.show_summary is None else request.show_summary,
        output_path=request.output,
        show=request.show,
        figsize=request.figsize,
    )


def _merge_histogram_compare_config(
    config: HistogramCompareConfig,
    *,
    request: CompareExampleRequest,
) -> HistogramCompareConfig:
    return replace(
        config,
        left_label=request.left_label or config.left_label,
        right_label=request.right_label or config.right_label,
        sort=config.sort if request.sort is None else request.sort,
        top_k=config.top_k if request.top_k is None else request.top_k,
        output_path=request.output,
        show=request.show,
        figsize=request.figsize,
    )


def _normalize_figsize(value: object) -> tuple[float, float]:
    if not isinstance(value, tuple | list) or len(value) != 2:
        raise SystemExit("--figsize must contain width and height.")
    figure_width = float(value[0])
    figure_height = float(value[1])
    if figure_width <= 0.0 or figure_height <= 0.0:
        raise SystemExit("--figsize values must be positive.")
    return figure_width, figure_height


def _optional_top_k(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise SystemExit("--top-k must be an integer.")
    parsed_value = int(value)
    if parsed_value < 1:
        raise SystemExit("--top-k must be at least 1.")
    return parsed_value


def _optional_sort(value: object) -> HistogramCompareSortName | None:
    if value is None:
        return None
    sort = str(value)
    if sort not in {"state", "state_desc", "delta_desc"}:
        raise SystemExit("--sort must be one of: state, state_desc, delta_desc.")
    return cast(HistogramCompareSortName, sort)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_bool(value: object) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise SystemExit("Boolean compare options must be true or false.")


def _set_compare_figure_title(*, figure: object, title: str) -> None:
    if hasattr(figure, "set_label"):
        figure.set_label(title)
    canvas = getattr(figure, "canvas", None)
    manager = getattr(canvas, "manager", None)
    if manager is None or not hasattr(manager, "set_window_title"):
        return
    try:
        manager.set_window_title(title)
    except Exception:
        return
