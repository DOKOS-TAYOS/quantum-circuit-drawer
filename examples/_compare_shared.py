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

try:
    from ._render_support import (
        normalize_figsize,
        release_rendered_result,
        set_result_figure_titles,
    )
except ImportError:
    from _render_support import normalize_figsize, release_rendered_result, set_result_figure_titles

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitCompareConfig,
    CircuitCompareOptions,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    compare_circuits,
    compare_histograms,
)
from quantum_circuit_drawer.histogram import (  # noqa: E402
    HistogramCompareConfig,
    HistogramCompareOptions,
    HistogramDataOptions,
)

CompareKind = Literal["circuits", "histograms"]
HistogramCompareSortName = Literal["state", "state_desc", "delta_desc"]
CircuitCompareModeName = Literal["auto", "pages", "pages_controls", "slider", "full"]
DEFAULT_COMPARE_FIGSIZE = (8.8, 4.8)


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
    mode: CircuitCompareModeName = "pages_controls"


@dataclass(frozen=True, slots=True)
class CompareDemoPayload:
    """Payload for one compare demo plus its default config."""

    compare_kind: CompareKind
    left_data: object
    right_data: object
    config: CircuitCompareConfig | HistogramCompareConfig
    extra_data: tuple[object, ...] = ()


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
        "--mode",
        choices=("auto", "pages", "pages_controls", "slider", "full"),
        default="pages_controls",
        help=(
            "Circuit compare render mode. Circuit demos default to pages_controls so "
            "the two circuits and summary table open as separate windows."
        ),
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
        figsize=normalize_figsize(getattr(args, "figsize", DEFAULT_COMPARE_FIGSIZE)),
        left_label=_optional_str(getattr(args, "left_label", None)),
        right_label=_optional_str(getattr(args, "right_label", None)),
        highlight_differences=_optional_bool(getattr(args, "highlight_differences", None)),
        show_summary=_optional_bool(getattr(args, "show_summary", None)),
        sort=_optional_sort(getattr(args, "sort", None)),
        top_k=_optional_top_k(getattr(args, "top_k", None)),
        mode=_optional_compare_mode(getattr(args, "mode", "pages_controls")),
    )


def render_compare_example(
    payload: CompareDemoPayload,
    *,
    request: CompareExampleRequest,
    saved_label: str,
) -> None:
    """Render one compare payload and optionally report the saved file."""

    result: object | None = None
    try:
        if payload.compare_kind == "circuits":
            config = _merge_circuit_compare_config(
                cast(CircuitCompareConfig, payload.config),
                request=request,
            )
            result = compare_circuits(
                payload.left_data,
                payload.right_data,
                *payload.extra_data,
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
                *payload.extra_data,
                config=config,
            )
        set_result_figure_titles(result=result, saved_label=saved_label)
        if request.output is not None:
            print(f"Saved {saved_label} to {request.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


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
    titles = _merge_optional_labels(
        config.titles,
        first_label=request.left_label,
        second_label=request.right_label,
    )
    shared = DrawSideConfig(
        render=replace(config.shared.render, mode=DrawMode(request.mode)),
        appearance=config.shared.appearance,
    )
    return CircuitCompareConfig(
        shared=shared,
        left_render=config.left_render,
        right_render=config.right_render,
        left_appearance=config.left_appearance,
        right_appearance=config.right_appearance,
        compare=CircuitCompareOptions(
            left_title=request.left_label or config.left_title,
            right_title=request.right_label or config.right_title,
            highlight_differences=(
                config.highlight_differences
                if request.highlight_differences is None
                else request.highlight_differences
            ),
            show_summary=(
                config.show_summary if request.show_summary is None else request.show_summary
            ),
            titles=titles,
        ),
        output=OutputOptions(
            output_path=request.output,
            show=request.show,
            figsize=request.figsize,
        ),
    )


def _merge_histogram_compare_config(
    config: HistogramCompareConfig,
    *,
    request: CompareExampleRequest,
) -> HistogramCompareConfig:
    series_labels = _merge_optional_labels(
        config.series_labels,
        first_label=request.left_label,
        second_label=request.right_label,
    )
    return HistogramCompareConfig(
        data=HistogramDataOptions(
            kind=config.kind,
            top_k=config.top_k if request.top_k is None else request.top_k,
            qubits=config.qubits,
            result_index=config.result_index,
            data_key=config.data_key,
        ),
        compare=HistogramCompareOptions(
            sort=config.sort if request.sort is None else request.sort,
            left_label=request.left_label or config.left_label,
            right_label=request.right_label or config.right_label,
            hover=config.hover,
            preset=config.preset,
            theme=config.theme,
            series_labels=series_labels,
        ),
        output=OutputOptions(
            output_path=request.output,
            show=request.show,
            figsize=request.figsize,
        ),
    )


def _merge_optional_labels(
    labels: tuple[str, ...] | None,
    *,
    first_label: str | None,
    second_label: str | None,
) -> tuple[str, ...] | None:
    if labels is None:
        return None
    if len(labels) < 2:
        return labels
    return (
        first_label or labels[0],
        second_label or labels[1],
        *labels[2:],
    )


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


def _optional_compare_mode(value: object) -> CircuitCompareModeName:
    mode = str(value)
    if mode not in {"auto", "pages", "pages_controls", "slider", "full"}:
        raise SystemExit("--mode must be one of: auto, pages, pages_controls, slider, full.")
    return cast(CircuitCompareModeName, mode)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_bool(value: object) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise SystemExit("Boolean compare options must be true or false.")
