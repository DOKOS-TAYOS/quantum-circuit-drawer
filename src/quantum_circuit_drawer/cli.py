"""Small command-line interface for common rendering workflows."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import cast

from .api import draw_quantum_circuit
from .config import (
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
)
from .histogram import plot_histogram
from .plots.histogram_models import (
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramDrawStyle,
    HistogramKind,
    HistogramMode,
    HistogramSort,
    HistogramStateLabelMode,
    HistogramViewOptions,
)

_CommandHandler = Callable[[Namespace], int]


class CliUsageError(Exception):
    """User-facing CLI argument or input-data error."""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``qcd`` command-line interface and return a process exit code."""

    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        handler = cast("_CommandHandler", args.handler)
        return handler(args)
    except CliUsageError as exc:
        parser.print_usage(sys.stderr)
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 2
    except SystemExit as exc:
        return _exit_code(exc.code)
    except Exception as exc:
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> ArgumentParser:
    """Build the top-level CLI parser."""

    parser = ArgumentParser(
        prog="qcd",
        description="Generate quantum circuit and histogram images from the terminal.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    draw_parser = subparsers.add_parser("draw", help="Draw an OpenQASM circuit image.")
    _add_draw_arguments(draw_parser)
    draw_parser.set_defaults(handler=run_draw_command)

    histogram_parser = subparsers.add_parser(
        "histogram",
        help="Plot a counts or quasi-probability JSON file.",
    )
    _add_histogram_arguments(histogram_parser)
    histogram_parser.set_defaults(handler=run_histogram_command)

    return parser


def run_draw_command(args: Namespace) -> int:
    """Render one circuit from CLI arguments."""

    output_path = cast(Path, args.output)
    result = draw_quantum_circuit(
        cast(str, args.input),
        config=_draw_config_from_args(args),
    )
    print(f"Saved circuit to {_saved_path(result, fallback=output_path)}")
    if not bool(args.show):
        _close_result_figures(result)
    return 0


def run_histogram_command(args: Namespace) -> int:
    """Render one histogram from a JSON file."""

    output_path = cast(Path, args.output)
    data = _selected_json_payload(_load_json_payload(cast(Path, args.input)), args.data_key)
    result = plot_histogram(
        data,
        config=_histogram_config_from_args(args),
    )
    print(f"Saved histogram to {_saved_path(result, fallback=output_path)}")
    if not bool(args.show):
        _close_result_figures(result)
    return 0


def _add_draw_arguments(parser: ArgumentParser) -> None:
    parser.add_argument("input", help="OpenQASM text or a .qasm/.qasm3 file path.")
    parser.add_argument("--output", required=True, type=Path, help="Output image path.")
    parser.add_argument("--view", choices=("2d", "3d"), default="2d")
    parser.add_argument(
        "--mode",
        choices=("auto", "pages", "pages_controls", "slider", "full"),
        default="pages",
    )
    parser.add_argument("--framework", help="Optional input framework override.")
    parser.add_argument(
        "--topology",
        choices=("line", "grid", "star", "star_tree", "honeycomb"),
        default="line",
    )
    parser.add_argument("--topology-qubits", choices=("used", "all"), default="used")
    parser.add_argument("--topology-resize", choices=("error", "fit"), default="error")
    parser.add_argument(
        "--preset",
        choices=("paper", "notebook", "compact", "presentation", "accessible"),
    )
    parser.add_argument("--composite-mode", choices=("compact", "expand"), default="compact")
    parser.add_argument("--unsupported-policy", choices=("raise", "placeholder"), default="raise")
    parser.add_argument(
        "--figsize",
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        type=_positive_float,
    )
    parser.add_argument("--show", action="store_true", help="Open the Matplotlib window.")


def _add_histogram_arguments(parser: ArgumentParser) -> None:
    parser.add_argument("input", type=Path, help="JSON file with histogram data.")
    parser.add_argument("--output", required=True, type=Path, help="Output image path.")
    parser.add_argument("--kind", choices=("auto", "counts", "quasi"), default="auto")
    parser.add_argument(
        "--sort",
        choices=("state", "state_desc", "value_desc", "value_asc"),
        default="state",
    )
    parser.add_argument("--top-k", type=_positive_int)
    parser.add_argument("--qubits", nargs="+", type=_non_negative_int)
    parser.add_argument("--data-key", help="Select a nested JSON field before plotting.")
    parser.add_argument("--state-label-mode", choices=("binary", "decimal"), default="binary")
    parser.add_argument(
        "--preset",
        choices=("paper", "notebook", "compact", "presentation", "accessible"),
    )
    parser.add_argument("--theme", choices=("light", "dark", "paper", "accessible"))
    parser.add_argument("--draw-style", choices=("solid", "outline", "soft"), default="solid")
    parser.add_argument(
        "--uniform-reference",
        action="store_true",
        help="Show the uniform reference baseline.",
    )
    parser.add_argument(
        "--figsize",
        nargs=2,
        metavar=("WIDTH", "HEIGHT"),
        type=_positive_float,
    )
    parser.add_argument("--show", action="store_true", help="Open the Matplotlib window.")


def _draw_config_from_args(args: Namespace) -> DrawConfig:
    view = cast(str, args.view)
    return DrawConfig(
        side=DrawSideConfig(
            render=CircuitRenderOptions(
                framework=args.framework,
                view=view,  # type: ignore[arg-type]
                mode=DrawMode(cast(str, args.mode)),
                composite_mode=cast(str, args.composite_mode),
                topology=args.topology,  # type: ignore[arg-type]
                topology_qubits=args.topology_qubits,  # type: ignore[arg-type]
                topology_resize=args.topology_resize,  # type: ignore[arg-type]
                direct=False if view == "3d" else True,
                unsupported_policy=args.unsupported_policy,  # type: ignore[arg-type]
            ),
            appearance=CircuitAppearanceOptions(preset=args.preset),
        ),
        output=OutputOptions(
            show=bool(args.show),
            output_path=cast(Path, args.output),
            figsize=_optional_figsize(args.figsize),
        ),
    )


def _histogram_config_from_args(args: Namespace) -> HistogramConfig:
    return HistogramConfig(
        data=HistogramDataOptions(
            kind=HistogramKind(cast(str, args.kind)),
            top_k=args.top_k,
            qubits=_optional_qubits(args.qubits),
            data_key=None,
        ),
        view=HistogramViewOptions(
            mode=HistogramMode.STATIC,
            sort=HistogramSort(cast(str, args.sort)),
            state_label_mode=HistogramStateLabelMode(cast(str, args.state_label_mode)),
        ),
        appearance=HistogramAppearanceOptions(
            preset=args.preset,
            theme=args.theme,
            draw_style=HistogramDrawStyle(cast(str, args.draw_style)),
            show_uniform_reference=bool(args.uniform_reference),
        ),
        output=OutputOptions(
            show=bool(args.show),
            output_path=cast(Path, args.output),
            figsize=_optional_figsize(args.figsize),
        ),
    )


def _load_json_payload(path: Path) -> object:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CliUsageError(f"could not read JSON file {path}: {exc}") from exc
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CliUsageError(
            f"Invalid JSON in {path}: {exc.msg} at line {exc.lineno}, column {exc.colno}"
        ) from exc


def _selected_json_payload(payload: object, data_key: object) -> object:
    if data_key is None:
        return payload
    if not isinstance(payload, Mapping):
        raise CliUsageError("--data-key requires a JSON object at the top level")
    key = str(data_key)
    if key not in payload:
        raise CliUsageError(f"JSON object does not contain key {key!r}")
    return payload[key]


def _optional_figsize(value: object) -> tuple[float, float] | None:
    if value is None:
        return None
    width, height = cast("Sequence[float]", value)
    return (float(width), float(height))


def _optional_qubits(value: object) -> tuple[int, ...] | None:
    if value is None:
        return None
    return tuple(cast("Sequence[int]", value))


def _positive_int(value: str) -> int:
    try:
        parsed_value = int(value)
    except ValueError as exc:
        raise CliUsageError("expected a positive integer") from exc
    if parsed_value < 1:
        raise CliUsageError("expected a positive integer")
    return parsed_value


def _non_negative_int(value: str) -> int:
    try:
        parsed_value = int(value)
    except ValueError as exc:
        raise CliUsageError("expected a non-negative integer") from exc
    if parsed_value < 0:
        raise CliUsageError("expected a non-negative integer")
    return parsed_value


def _positive_float(value: str) -> float:
    try:
        parsed_value = float(value)
    except ValueError as exc:
        raise CliUsageError("expected a positive number") from exc
    if parsed_value <= 0.0:
        raise CliUsageError("expected a positive number")
    return parsed_value


def _saved_path(result: object, *, fallback: Path) -> str:
    saved_path = getattr(result, "saved_path", None)
    return str(saved_path) if saved_path is not None else str(fallback.resolve())


def _close_result_figures(result: object) -> None:
    from matplotlib import pyplot as plt

    figures = getattr(result, "figures", None)
    if figures is None:
        figure = getattr(result, "figure", None)
        figures = () if figure is None else (figure,)
    for figure in figures:
        plt.close(figure)


def _exit_code(value: object) -> int:
    if isinstance(value, int):
        return value
    if value is None:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
