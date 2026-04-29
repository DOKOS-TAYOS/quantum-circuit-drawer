"""Shared helpers for histogram example entrypoints."""

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
    from ._render_support import normalize_figsize, release_rendered_result, set_figure_title
except ImportError:
    from _render_support import normalize_figsize, release_rendered_result, set_figure_title

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramViewOptions,
    OutputOptions,
    plot_histogram,
)

DEFAULT_HISTOGRAM_FIGSIZE = (10.1, 5.5)
HistogramModeName = Literal["auto", "static", "interactive"]
HistogramSortName = Literal["state", "state_desc", "value_desc", "value_asc"]
HistogramDrawStyleName = Literal["solid", "outline", "soft"]
HistogramStateLabelModeName = Literal["binary", "decimal"]


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


def demo_multi_register_counts_data() -> dict[str, int]:
    """Return a shared counts payload with two classical-register groups."""

    return {
        "00 000": 12,
        "00 101": 29,
        "01 011": 21,
        "10 001": 37,
        "10 111": 18,
        "11 010": 33,
    }


@dataclass(frozen=True, slots=True)
class HistogramExampleRequest:
    """Normalized render request shared by histogram example scripts."""

    output: Path | None
    show: bool
    figsize: tuple[float, float]
    mode: HistogramModeName | None = None
    sort: HistogramSortName | None = None
    top_k: int | None = None
    qubits: tuple[int, ...] | None = None
    result_index: int | None = None
    data_key: str | None = None
    preset: str | None = None
    theme: str | None = None
    draw_style: HistogramDrawStyleName | None = None
    state_label_mode: HistogramStateLabelModeName | None = None
    hover: bool | None = None
    show_uniform_reference: bool | None = None


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
        "--mode",
        choices=("auto", "static", "interactive"),
        help="Optional histogram mode override.",
    )
    parser.add_argument(
        "--sort",
        choices=("state", "state_desc", "value_desc", "value_asc"),
        help="Optional histogram ordering override.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="Optionally keep only the top-k visible states.",
    )
    parser.add_argument(
        "--qubits",
        nargs="+",
        type=int,
        help="Optional qubit subset for a joint marginal, for example: --qubits 0 2 5.",
    )
    parser.add_argument(
        "--result-index",
        type=int,
        help="Optional index used when the framework returned several histogram payloads.",
    )
    parser.add_argument(
        "--data-key",
        help="Optional key used when a framework result exposes several histogram fields.",
    )
    parser.add_argument(
        "--preset",
        choices=("paper", "notebook", "compact", "presentation", "accessible"),
        help="Optional style preset applied before explicit overrides.",
    )
    parser.add_argument(
        "--theme",
        choices=("light", "dark", "paper", "accessible"),
        help="Optional histogram theme override.",
    )
    parser.add_argument(
        "--draw-style",
        choices=("solid", "outline", "soft"),
        help="Optional histogram bar style override.",
    )
    parser.add_argument(
        "--state-label-mode",
        choices=("binary", "decimal"),
        help="Optional visible state-label mode override.",
    )
    parser.add_argument(
        "--hover",
        dest="hover",
        action="store_true",
        default=None,
        help="Enable histogram hover when the mode supports it.",
    )
    parser.add_argument(
        "--no-hover",
        dest="hover",
        action="store_false",
        help="Disable histogram hover when the mode supports it.",
    )
    parser.add_argument(
        "--uniform-reference",
        dest="show_uniform_reference",
        action="store_true",
        default=None,
        help="Show the uniform reference line.",
    )
    parser.add_argument(
        "--no-uniform-reference",
        dest="show_uniform_reference",
        action="store_false",
        help="Hide the uniform reference line.",
    )
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
        mode=_optional_histogram_mode(getattr(args, "mode", None)),
        sort=_optional_histogram_sort(getattr(args, "sort", None)),
        top_k=_optional_non_negative_int(getattr(args, "top_k", None), "--top-k", minimum=1),
        qubits=_optional_qubit_subset(getattr(args, "qubits", None)),
        result_index=_optional_non_negative_int(
            getattr(args, "result_index", None),
            "--result-index",
            minimum=0,
        ),
        data_key=_optional_str(getattr(args, "data_key", None)),
        preset=_optional_choice(
            getattr(args, "preset", None),
            option_name="--preset",
            allowed_values=("paper", "notebook", "compact", "presentation", "accessible"),
        ),
        theme=_optional_choice(
            getattr(args, "theme", None),
            option_name="--theme",
            allowed_values=("light", "dark", "paper", "accessible"),
        ),
        draw_style=_optional_histogram_draw_style(getattr(args, "draw_style", None)),
        state_label_mode=_optional_state_label_mode(getattr(args, "state_label_mode", None)),
        hover=_optional_bool(getattr(args, "hover", None)),
        show_uniform_reference=_optional_bool(getattr(args, "show_uniform_reference", None)),
        output=args.output,
        show=bool(args.show),
        figsize=normalize_figsize(args.figsize),
    )


def render_histogram_example(
    payload: HistogramDemoPayload,
    *,
    request: HistogramExampleRequest,
    saved_label: str,
) -> None:
    """Plot one built histogram payload and optionally report the saved file."""

    result: object | None = None
    try:
        config = build_histogram_config(payload.config, request=request)
        result = plot_histogram(payload.data, config=config)
        set_figure_title(figure=result.figure, title=saved_label)
        if request.output is not None:
            print(f"Saved {saved_label} to {request.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


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


def build_histogram_config(
    base_config: HistogramConfig,
    *,
    request: HistogramExampleRequest,
) -> HistogramConfig:
    """Merge one request into a histogram config while keeping demo defaults."""

    resolved_data = replace(
        base_config.data,
        top_k=base_config.top_k if request.top_k is None else request.top_k,
        qubits=base_config.qubits if request.qubits is None else request.qubits,
        result_index=(
            base_config.result_index if request.result_index is None else request.result_index
        ),
        data_key=base_config.data_key if request.data_key is None else request.data_key,
    )
    resolved_view = replace(
        base_config.view,
        mode=base_config.mode if request.mode is None else request.mode,
        sort=base_config.sort if request.sort is None else request.sort,
        state_label_mode=(
            base_config.state_label_mode
            if request.state_label_mode is None
            else request.state_label_mode
        ),
    )
    resolved_appearance = replace(
        base_config.appearance,
        preset=base_config.preset if request.preset is None else request.preset,
        theme=base_config.theme if request.theme is None else request.theme,
        draw_style=base_config.draw_style if request.draw_style is None else request.draw_style,
        hover=base_config.hover if request.hover is None else request.hover,
        show_uniform_reference=(
            base_config.show_uniform_reference
            if request.show_uniform_reference is None
            else request.show_uniform_reference
        ),
    )
    return HistogramConfig(
        data=HistogramDataOptions(
            kind=resolved_data.kind,
            top_k=resolved_data.top_k,
            qubits=resolved_data.qubits,
            result_index=resolved_data.result_index,
            data_key=resolved_data.data_key,
        ),
        view=HistogramViewOptions(
            mode=resolved_view.mode,
            sort=resolved_view.sort,
            state_label_mode=resolved_view.state_label_mode,
        ),
        appearance=HistogramAppearanceOptions(
            preset=resolved_appearance.preset,
            theme=resolved_appearance.theme,
            draw_style=resolved_appearance.draw_style,
            hover=resolved_appearance.hover,
            show_uniform_reference=resolved_appearance.show_uniform_reference,
        ),
        output=OutputOptions(
            output_path=request.output,
            show=request.show,
            figsize=request.figsize,
        ),
    )


def _optional_histogram_mode(value: object) -> HistogramModeName | None:
    if value is None:
        return None
    mode = str(value)
    if mode not in {"auto", "static", "interactive"}:
        raise SystemExit("--mode must be one of: auto, static, interactive.")
    return cast(HistogramModeName, mode)


def _optional_histogram_sort(value: object) -> HistogramSortName | None:
    if value is None:
        return None
    sort = str(value)
    if sort not in {"state", "state_desc", "value_desc", "value_asc"}:
        raise SystemExit("--sort must be one of: state, state_desc, value_desc, value_asc.")
    return cast(HistogramSortName, sort)


def _optional_histogram_draw_style(value: object) -> HistogramDrawStyleName | None:
    if value is None:
        return None
    draw_style = str(value)
    if draw_style not in {"solid", "outline", "soft"}:
        raise SystemExit("--draw-style must be one of: solid, outline, soft.")
    return cast(HistogramDrawStyleName, draw_style)


def _optional_state_label_mode(value: object) -> HistogramStateLabelModeName | None:
    if value is None:
        return None
    state_label_mode = str(value)
    if state_label_mode not in {"binary", "decimal"}:
        raise SystemExit("--state-label-mode must be one of: binary, decimal.")
    return cast(HistogramStateLabelModeName, state_label_mode)


def _optional_non_negative_int(
    value: object,
    option_name: str,
    *,
    minimum: int,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise SystemExit(f"{option_name} must be an integer.")
    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as error:
        raise SystemExit(f"{option_name} must be an integer.") from error
    if parsed_value < minimum:
        comparator = "at least 1" if minimum == 1 else "a non-negative integer"
        raise SystemExit(f"{option_name} must be {comparator}.")
    return parsed_value


def _optional_qubit_subset(value: object) -> tuple[int, ...] | None:
    if value is None:
        return None
    if isinstance(value, tuple):
        qubits = value
    elif isinstance(value, list):
        qubits = tuple(value)
    else:
        raise SystemExit("--qubits must be a sequence of non-negative integers.")
    normalized_qubits = tuple(int(qubit) for qubit in qubits)
    if any(qubit < 0 for qubit in normalized_qubits):
        raise SystemExit("--qubits must contain only non-negative integers.")
    if len(set(normalized_qubits)) != len(normalized_qubits):
        raise SystemExit("--qubits must not contain duplicates.")
    return normalized_qubits


def _optional_choice(
    value: object,
    *,
    option_name: str,
    allowed_values: tuple[str, ...],
) -> str | None:
    if value is None:
        return None
    choice = str(value)
    if choice not in allowed_values:
        raise SystemExit(f"{option_name} must be one of: {', '.join(allowed_values)}.")
    return choice


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_bool(value: object) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise SystemExit("Boolean example options must be true or false.")
