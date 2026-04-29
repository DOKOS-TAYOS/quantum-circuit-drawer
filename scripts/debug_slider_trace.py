"""Trace managed 2D slider interactions in a real interactive window."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, TextIO, cast

from matplotlib import pyplot as plt
from matplotlib.backend_bases import KeyEvent, MouseEvent

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
for candidate in (SOURCE_ROOT, PROJECT_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from examples._render_support import release_rendered_result  # noqa: E402
from examples.qiskit_2d_exploration_showcase import (  # noqa: E402
    build_circuit as build_exploration_circuit,
)
from examples.qiskit_random import build_circuit as build_random_circuit  # noqa: E402

from quantum_circuit_drawer import (  # noqa: E402
    CircuitAppearanceOptions,
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)
from quantum_circuit_drawer.managed.slider import Managed2DPageSliderState  # noqa: E402
from quantum_circuit_drawer.renderers._matplotlib_figure import get_page_slider  # noqa: E402


def main() -> None:
    """Open one interactive slider demo and write a detailed trace to disk."""

    args = _parse_args()
    log_path = args.log_file.resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log_file = log_path.open("w", encoding="utf-8")
    try:
        print(f"Writing slider trace to {log_path}")
        print("Interact with the window, then close it.")
        _run_trace(args, log_file)
    finally:
        log_file.close()

    print(f"Trace saved to {log_path}")
    print(f"Show the last lines with: Get-Content '{log_path}' -Tail 80")


def _run_trace(args: Namespace, log_file: TextIO) -> None:
    """Render the requested demo, attach tracing hooks, and enter the GUI loop."""

    real_show = plt.show
    plt.show = _noop_show
    result = None
    try:
        result = draw_quantum_circuit(
            _build_demo_circuit(args),
            config=DrawConfig(
                side=DrawSideConfig(
                    render=CircuitRenderOptions(
                        mode=DrawMode.SLIDER,
                        topology=args.topology,
                    ),
                    appearance=CircuitAppearanceOptions(hover=True),
                ),
                output=OutputOptions(
                    show=True,
                    figsize=(11.8, 6.2),
                ),
            ),
        )
    finally:
        plt.show = real_show

    if result is None:
        raise RuntimeError("Expected an interactive draw result but got none.")

    try:
        figure = result.primary_figure
        figure.canvas.draw()
        page_slider = cast(Managed2DPageSliderState | None, get_page_slider(figure))
        if page_slider is None:
            raise RuntimeError("Managed 2D page slider state was not attached to the figure.")

        _install_trace(page_slider, log_file)
        _write_trace(
            log_file,
            event="trace.ready",
            payload={
                "canvas_type": type(figure.canvas).__name__,
                "manager_type": type(getattr(figure.canvas, "manager", None)).__name__,
                "toolbar_type": type(
                    getattr(getattr(figure.canvas, "manager", None), "toolbar", None)
                ).__name__,
                **_state_snapshot(page_slider),
            },
        )
        real_show()
        _write_trace(
            log_file,
            event="trace.closed",
            payload=_state_snapshot(page_slider),
        )
    finally:
        release_rendered_result(result)


def _noop_show(*args: object, **kwargs: object) -> None:
    """Temporarily suppress pyplot.show() while we attach trace hooks."""


def _build_demo_circuit(args: Namespace) -> object:
    """Build the requested example circuit."""

    if args.demo == "exploration":
        return build_exploration_circuit(
            qubit_count=args.qubits,
            motif_count=args.columns,
        )
    if args.demo == "random":
        return build_random_circuit(
            qubit_count=args.qubits,
            column_count=args.columns,
            seed=args.seed,
        )
    raise ValueError(f"Unsupported demo: {args.demo}")


def _install_trace(state: Managed2DPageSliderState, log_file: TextIO) -> None:
    """Attach raw GUI and slider-value tracing without mutating slotted state."""

    canvas = getattr(state.figure, "canvas", None)
    if canvas is None:
        return

    if state.horizontal_slider is not None:
        state.horizontal_slider.on_changed(
            lambda value: _write_trace(
                log_file,
                event="horizontal_slider.changed",
                payload={
                    "requested_slider_value": float(value),
                    **_state_snapshot(state),
                },
            )
        )

    def on_key(event: KeyEvent) -> None:
        _write_trace(
            log_file,
            event="canvas.key_press",
            payload={
                "key": event.key,
                "inaxes": _inaxes_name(state, getattr(event, "inaxes", None)),
                **_state_snapshot(state),
            },
        )

    def on_button(event: MouseEvent) -> None:
        if getattr(event, "inaxes", None) not in {state.axes, state.horizontal_axes}:
            return
        _write_trace(
            log_file,
            event=event.name,
            payload={
                "button": event.button,
                "dblclick": bool(getattr(event, "dblclick", False)),
                "inaxes": _inaxes_name(state, event.inaxes),
                "x": float(event.x),
                "y": float(event.y),
                "xdata": None if event.xdata is None else float(event.xdata),
                "ydata": None if event.ydata is None else float(event.ydata),
                **_state_snapshot(state),
            },
        )

    def on_draw(_event: object) -> None:
        _write_trace(
            log_file,
            event="canvas.draw",
            payload=_state_snapshot(state),
        )

    canvas.mpl_connect("key_press_event", on_key)
    canvas.mpl_connect("button_press_event", on_button)
    canvas.mpl_connect("button_release_event", on_button)
    canvas.mpl_connect("draw_event", on_draw)


def _state_snapshot(state: Managed2DPageSliderState) -> dict[str, Any]:
    """Return one compact snapshot of the current slider state."""

    visible_labels = [
        gate.label
        for gate in sorted(
            state.scene.gates,
            key=lambda gate: (gate.column, gate.y, gate.x, gate.label),
        )[:8]
    ]
    current_page = state.scene.pages[0] if state.scene.pages else None
    previous_stop, next_stop = _neighbor_stops(state)
    rendered_texts = _rendered_axes_texts(state)
    return {
        "start_column": state.start_column,
        "max_start_column": state.max_start_column,
        "slider_value": (
            None if state.horizontal_slider is None else float(state.horizontal_slider.val)
        ),
        "stop_count": len(state.horizontal_slider_stops),
        "previous_stop": previous_stop,
        "next_stop": next_stop,
        "is_exact_stop": state.start_column in state.horizontal_slider_stops,
        "window_page_start": None if current_page is None else int(current_page.start_column),
        "window_page_end": None if current_page is None else int(current_page.end_column),
        "visible_gate_labels": visible_labels,
        "rendered_texts": rendered_texts,
        "axes_text_count": len(getattr(state.axes, "texts", ())),
    }


def _neighbor_stops(state: Managed2DPageSliderState) -> tuple[int | None, int | None]:
    """Return the nearest useful stops around the current start column."""

    previous_stop: int | None = None
    next_stop: int | None = None
    for stop in state.horizontal_slider_stops:
        if stop <= state.start_column:
            previous_stop = stop
        if stop >= state.start_column:
            next_stop = stop
            break
    return previous_stop, next_stop


def _rendered_axes_texts(state: Managed2DPageSliderState) -> list[str]:
    """Return a small ordered sample of the texts currently painted on the axes."""

    rendered_texts: list[str] = []
    seen_texts: set[str] = set()
    for text_artist in getattr(state.axes, "texts", ()):
        get_text = getattr(text_artist, "get_text", None)
        if not callable(get_text):
            continue
        text = str(get_text()).strip()
        if not text or text in seen_texts:
            continue
        seen_texts.add(text)
        rendered_texts.append(text)
        if len(rendered_texts) >= 12:
            break
    return rendered_texts


def _inaxes_name(state: Managed2DPageSliderState, inaxes: object | None) -> str | None:
    """Return a short stable name for the current axes target."""

    if inaxes is None:
        return None
    if inaxes is state.axes:
        return "main_axes"
    if inaxes is state.horizontal_axes:
        return "horizontal_slider_axes"
    return type(inaxes).__name__


def _write_trace(
    log_file: TextIO,
    *,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Write one JSONL trace event and flush it immediately."""

    line = {
        "event": event,
        **payload,
    }
    log_file.write(json.dumps(line, ensure_ascii=True) + "\n")
    log_file.flush()


def _parse_args() -> Namespace:
    """Parse CLI arguments for the manual trace helper."""

    parser = ArgumentParser(description="Trace one managed 2D slider session to a JSONL file.")
    parser.add_argument(
        "--demo",
        choices=("exploration", "random"),
        default="exploration",
        help="Which interactive demo circuit to open.",
    )
    parser.add_argument(
        "--columns",
        type=int,
        default=9,
        help="Motif count for the exploration demo or column count for the random demo.",
    )
    parser.add_argument(
        "--qubits",
        type=int,
        default=12,
        help="Quantum wire count to use for the selected demo.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Seed used by the random demo.",
    )
    parser.add_argument(
        "--topology",
        choices=("line", "grid", "star", "star_tree", "honeycomb"),
        default="grid",
        help="Topology passed through to the interactive 2D render.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path("test_tmp") / "slider_trace.jsonl",
        help="Where to write the JSONL trace.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
