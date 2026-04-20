"""Shared helpers for configurable example entrypoints."""

from __future__ import annotations

import re
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

try:
    from ._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    DrawConfig,
    DrawMode,
    HoverOptions,
    draw_quantum_circuit,
)

ViewMode = Literal["2d", "3d"]
RenderMode = Literal["pages", "pages_controls", "slider", "full"]
TopologyMode = Literal["line", "grid", "star", "star_tree", "honeycomb"]
HoverMatrixMode = Literal["never", "auto", "always"]

SUPPORTED_TOPOLOGIES: tuple[TopologyMode, ...] = (
    "line",
    "grid",
    "star",
    "star_tree",
    "honeycomb",
)
DEFAULT_DEMO_FIGSIZE = (10.0, 5.5)


@dataclass(frozen=True, slots=True)
class ExampleRequest:
    """Normalized render request shared by the example scripts."""

    qubits: int
    columns: int
    mode: RenderMode
    view: ViewMode
    topology: TopologyMode
    seed: int
    output: Path | None
    show: bool
    figsize: tuple[float, float]
    hover: bool
    hover_matrix: HoverMatrixMode
    hover_matrix_max_qubits: int
    hover_show_size: bool


ExampleBuilder = Callable[[ExampleRequest], object]


def add_render_arguments(
    parser: ArgumentParser,
    *,
    default_qubits: int | None,
    default_columns: int | None,
    columns_help: str,
    default_seed: int = 7,
) -> None:
    """Attach the shared render arguments to one example parser."""

    default_figure_width, default_figure_height = DEFAULT_DEMO_FIGSIZE
    qubits_help = "Quantum wires to generate."
    if default_qubits is not None:
        qubits_help = f"{qubits_help} Default: {default_qubits}."

    normalized_columns_help = columns_help.rstrip(".")
    if default_columns is not None:
        normalized_columns_help = f"{normalized_columns_help}. Default: {default_columns}."
    else:
        normalized_columns_help = f"{normalized_columns_help}."

    parser.add_argument("--qubits", type=int, default=None, help=qubits_help)
    parser.add_argument(
        "--columns",
        type=int,
        default=default_columns,
        help=normalized_columns_help,
    )
    parser.add_argument(
        "--mode",
        choices=("pages", "pages_controls", "slider", "full"),
        default="pages",
        help=(
            "Render page figures, a managed page viewer, a slider, or the full unpaged scene. "
            "In 3D, pages_controls stacks the visible pages vertically."
        ),
    )
    parser.add_argument(
        "--view",
        choices=("2d", "3d"),
        default="2d",
        help="Choose the 2D or topology-aware 3D renderer.",
    )
    parser.add_argument(
        "--topology",
        choices=SUPPORTED_TOPOLOGIES,
        default="line",
        help="3D topology. It is ignored in 2D mode.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=default_seed,
        help="Seed used by the random demos.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the rendered figure will also be saved.",
    )
    parser.add_argument(
        "--figsize",
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        type=float,
        default=DEFAULT_DEMO_FIGSIZE,
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
    parser.add_argument(
        "--hover",
        dest="hover",
        action="store_true",
        default=True,
        help="Enable hover tooltips when the Matplotlib backend supports them.",
    )
    parser.add_argument(
        "--no-hover",
        dest="hover",
        action="store_false",
        help="Disable hover tooltips.",
    )
    parser.add_argument(
        "--hover-matrix",
        choices=("never", "auto", "always"),
        default="auto",
        help="Control whether hover tooltips include the gate matrix.",
    )
    parser.add_argument(
        "--hover-matrix-max-qubits",
        type=int,
        default=2,
        help="Maximum gate width, in qubits, for showing full matrices in hover.",
    )
    parser.add_argument(
        "--hover-show-size",
        action="store_true",
        help="Also include the visual gate size in the hover tooltip.",
    )


def parse_example_args(
    *,
    description: str,
    default_qubits: int,
    default_columns: int,
    columns_help: str,
    default_seed: int = 7,
) -> ExampleRequest:
    """Parse and validate the shared command-line arguments."""

    parser = ArgumentParser(description=description)
    add_render_arguments(
        parser,
        default_qubits=default_qubits,
        default_columns=default_columns,
        columns_help=columns_help,
        default_seed=default_seed,
    )
    return request_from_namespace(
        parser.parse_args(),
        default_qubits=default_qubits,
        default_columns=default_columns,
    )


def request_from_namespace(
    args: Namespace,
    *,
    default_qubits: int,
    default_columns: int,
) -> ExampleRequest:
    """Normalize one parsed namespace into an example request."""

    columns = int(default_columns if args.columns is None else args.columns)
    mode = str(args.mode)
    view = str(args.view)
    topology = str(args.topology)
    valid_modes = {"pages", "pages_controls", "slider", "full"}
    valid_views = {"2d", "3d"}

    if columns < 1:
        raise SystemExit("--columns must be at least 1.")
    if mode not in valid_modes:
        raise SystemExit("--mode must be one of: pages, pages_controls, slider, full.")
    if view not in valid_views:
        raise SystemExit("--view must be one of: 2d, 3d.")
    if topology not in SUPPORTED_TOPOLOGIES:
        allowed_topologies = ", ".join(SUPPORTED_TOPOLOGIES)
        raise SystemExit(f"--topology must be one of: {allowed_topologies}.")
    qubits = _resolve_request_qubits(
        qubits=args.qubits,
        default_qubits=default_qubits,
        view=cast(ViewMode, view),
        topology=cast(TopologyMode, topology),
    )
    if qubits < 1:
        raise SystemExit("--qubits must be at least 1.")
    figure_width, figure_height = _normalize_figsize(args.figsize)
    hover_matrix_max_qubits = int(getattr(args, "hover_matrix_max_qubits", 2))
    if hover_matrix_max_qubits < 1:
        raise SystemExit("--hover-matrix-max-qubits must be at least 1.")
    hover_matrix = str(getattr(args, "hover_matrix", "auto"))
    if hover_matrix not in {"never", "auto", "always"}:
        hover_matrix = "auto"
    return ExampleRequest(
        qubits=qubits,
        columns=columns,
        mode=mode,
        view=view,
        topology=topology,
        seed=int(args.seed),
        output=args.output,
        show=bool(args.show),
        figsize=(figure_width, figure_height),
        hover=bool(getattr(args, "hover", True)),
        hover_matrix=hover_matrix,
        hover_matrix_max_qubits=hover_matrix_max_qubits,
        hover_show_size=bool(getattr(args, "hover_show_size", False)),
    )


def _resolve_request_qubits(
    *,
    qubits: object,
    default_qubits: int,
    view: ViewMode,
    topology: TopologyMode,
) -> int:
    if qubits is not None:
        return int(qubits)
    if view != "3d":
        return int(default_qubits)
    return _topology_compatible_default_qubits(
        default_qubits=default_qubits,
        topology=topology,
    )


def _topology_compatible_default_qubits(*, default_qubits: int, topology: TopologyMode) -> int:
    if topology == "line":
        return max(1, default_qubits)
    if topology == "grid":
        return _next_grid_wire_count(default_qubits)
    if topology == "star":
        return max(2, default_qubits)
    if topology == "star_tree":
        return _next_star_tree_wire_count(default_qubits)
    return 53


def _next_grid_wire_count(default_qubits: int) -> int:
    candidate = max(4, default_qubits)
    while True:
        for rows in range(2, int(candidate**0.5) + 1):
            if candidate % rows == 0 and (candidate // rows) >= 2:
                return candidate
        candidate += 1


def _next_star_tree_wire_count(default_qubits: int) -> int:
    candidate = max(4, default_qubits)
    depth = 1
    while ((3 * (2**depth)) - 2) < candidate:
        depth += 1
    return (3 * (2**depth)) - 2


def _normalize_figsize(value: object) -> tuple[float, float]:
    if not isinstance(value, tuple | list) or len(value) != 2:
        raise SystemExit("--figsize must contain width and height.")

    figure_width = float(value[0])
    figure_height = float(value[1])
    if figure_width <= 0.0 or figure_height <= 0.0:
        raise SystemExit("--figsize values must be positive.")
    return figure_width, figure_height


def demo_style(*, columns: int) -> dict[str, object]:
    """Return the shared example style tuned to the requested circuit width."""

    return {
        "font_size": 12.0,
        "show_params": True,
        "max_page_width": recommended_page_width(columns),
    }


def recommended_page_width(columns: int) -> float:
    """Return a strict page-width cap that grows with the requested width."""

    return min(12.0, max(6.5, 4.5 + (0.22 * float(columns))))


def demo_adapter_options(
    request: ExampleRequest,
    *,
    framework: str | None,
) -> dict[str, object]:
    """Return adapter options tuned for the current demo environment."""

    if not sys.platform.startswith("win"):
        return {}
    if framework not in {"cirq", "pennylane"}:
        return {}
    return {"explicit_matrices": request.hover_matrix == "always"}


def demo_hover_options(request: ExampleRequest) -> HoverOptions:
    """Return hover settings for the shared example scripts."""

    return HoverOptions(
        enabled=request.hover,
        show_size=request.hover_show_size,
        show_matrix=request.hover_matrix,
        matrix_max_qubits=request.hover_matrix_max_qubits,
    )


def build_draw_config(
    request: ExampleRequest,
    *,
    framework: str | None,
) -> DrawConfig:
    """Build the public draw configuration for one example render."""

    return DrawConfig(
        framework=framework,
        view=request.view,
        mode=DrawMode(request.mode),
        topology=request.topology,
        topology_menu=request.view == "3d" and request.mode in {"pages_controls", "slider"},
        direct=False if request.view == "3d" else True,
        show=request.show,
        output_path=request.output,
        figsize=request.figsize,
        style=demo_style(columns=request.columns),
        hover=demo_hover_options(request),
    )


def render_example(
    subject: object,
    *,
    request: ExampleRequest,
    framework: str | None,
    saved_label: str,
) -> None:
    """Draw one built example subject and optionally report the saved file."""

    config = build_draw_config(request, framework=framework)
    try:
        result = draw_quantum_circuit(
            subject,
            config=config,
        )
    except ValueError as error:
        friendly_error = _friendly_demo_render_error(request=request, error=error)
        if friendly_error is not None:
            raise friendly_error from None
        raise
    _set_demo_figure_titles(result=result, saved_label=saved_label)

    if request.output is not None:
        print(f"Saved {saved_label} to {request.output}")


def run_example(
    builder: ExampleBuilder,
    *,
    description: str,
    framework: str | None,
    saved_label: str,
    default_qubits: int,
    default_columns: int,
    columns_help: str,
    default_seed: int = 7,
) -> None:
    """Parse CLI options, build the subject, and render the example."""

    request = parse_example_args(
        description=description,
        default_qubits=default_qubits,
        default_columns=default_columns,
        columns_help=columns_help,
        default_seed=default_seed,
    )
    render_example(
        builder(request),
        request=request,
        framework=framework,
        saved_label=saved_label,
    )


def _set_demo_figure_titles(*, result: object, saved_label: str) -> None:
    figures = tuple(getattr(result, "figures", ()))
    if not figures:
        return

    total_figures = len(figures)
    for page_index, figure in enumerate(figures, start=1):
        title = (
            saved_label
            if total_figures == 1
            else f"{saved_label} - page {page_index}/{total_figures}"
        )
        if hasattr(figure, "set_label"):
            figure.set_label(title)
        _set_demo_window_title(figure=figure, title=title)


def _set_demo_window_title(*, figure: object, title: str) -> None:
    canvas = getattr(figure, "canvas", None)
    manager = getattr(canvas, "manager", None)
    if manager is None or not hasattr(manager, "set_window_title"):
        return

    try:
        manager.set_window_title(title)
    except Exception as error:
        if _is_destroyed_window_error(error):
            return
        raise


def _is_destroyed_window_error(error: Exception) -> bool:
    error_name = type(error).__name__
    if error_name not in {"TclError", "RuntimeError"}:
        return False

    normalized_message = str(error).lower()
    destroyed_markers = (
        "application has been destroyed",
        "already deleted",
        "has been deleted",
        "does not exist",
    )
    return any(marker in normalized_message for marker in destroyed_markers)


def _friendly_demo_render_error(
    *,
    request: ExampleRequest,
    error: ValueError,
) -> SystemExit | None:
    if request.view != "3d":
        return None

    match = re.search(
        r"topology '([^']+)' does not support (\d+) quantum wire(?:s)?",
        str(error),
    )
    if match is None:
        return None

    topology_name = match.group(1)
    wire_count = int(match.group(2))
    return SystemExit(
        f"3D topology '{topology_name}' is not available for this demo with {wire_count} qubits. "
        "Try another topology or change --qubits."
    )
