"""Shared helpers for configurable example entrypoints."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    from ._bootstrap import ensure_local_project_on_path
except ImportError:
    from _bootstrap import ensure_local_project_on_path

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import draw_quantum_circuit  # noqa: E402

ViewMode = Literal["2d", "3d"]
RenderMode = Literal["pages", "slider"]
TopologyMode = Literal["line", "grid", "star", "star_tree", "honeycomb"]

SUPPORTED_TOPOLOGIES: tuple[TopologyMode, ...] = (
    "line",
    "grid",
    "star",
    "star_tree",
    "honeycomb",
)
DEFAULT_DEMO_FIGSIZE = (14.0, 8.0)


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

    parser.add_argument("--qubits", type=int, default=default_qubits, help=qubits_help)
    parser.add_argument(
        "--columns",
        type=int,
        default=default_columns,
        help=normalized_columns_help,
    )
    parser.add_argument(
        "--mode",
        choices=("pages", "slider"),
        default="pages",
        help="Render in wrapped pages or in the horizontal slider view.",
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

    qubits = int(default_qubits if args.qubits is None else args.qubits)
    columns = int(default_columns if args.columns is None else args.columns)
    mode = str(args.mode)
    view = str(args.view)
    topology = str(args.topology)

    if qubits < 1:
        raise SystemExit("--qubits must be at least 1.")
    if columns < 1:
        raise SystemExit("--columns must be at least 1.")
    if view == "3d" and mode == "slider":
        raise SystemExit("Slider mode is only available in 2D. Use --mode pages with --view 3d.")
    figure_width, figure_height = _normalize_figsize(args.figsize)

    return ExampleRequest(
        qubits=qubits,
        columns=columns,
        mode=mode if mode in {"pages", "slider"} else "pages",
        view=view if view in {"2d", "3d"} else "2d",
        topology=topology if topology in SUPPORTED_TOPOLOGIES else "line",
        seed=int(args.seed),
        output=args.output,
        show=bool(args.show),
        figsize=(figure_width, figure_height),
    )


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


def build_render_options(request: ExampleRequest) -> dict[str, object]:
    """Return draw options derived from the shared example request."""

    if request.view == "2d":
        return {}
    return {
        "view": "3d",
        "topology": request.topology,
        "direct": False,
        "hover": True,
    }


def render_example(
    subject: object,
    *,
    request: ExampleRequest,
    framework: str | None,
    saved_label: str,
) -> None:
    """Draw one built example subject and optionally report the saved file."""

    draw_quantum_circuit(
        subject,
        framework=framework,
        style=demo_style(columns=request.columns),
        output=request.output,
        show=request.show,
        figsize=request.figsize,
        page_slider=request.mode == "slider",
        **build_render_options(request),
    )

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
