"""Hover helpers for interactive 2D Matplotlib rendering."""

from __future__ import annotations

from dataclasses import dataclass
from types import MethodType

import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent
from matplotlib.transforms import Bbox

from ..hover import HoverOptions
from ..layout.scene import SceneHoverData
from ._matplotlib_figure import HoverState, set_hover_state

_HOVER_ZORDER = 10_000
_SMALL_GATE_PIXEL_THRESHOLD = 48.0


@dataclass(frozen=True, slots=True)
class _HoverTarget2D:
    artist: Artist
    hover_data: SceneHoverData


def add_hover_target(
    axes: Axes,
    hover_targets: list[_HoverTarget2D],
    artist: Artist,
    hover_data: SceneHoverData,
) -> None:
    """Register one artist as hoverable, adding a stable extent fallback when needed."""

    _set_hover_artist_extent(axes, artist, hover_data)
    hover_targets.append(_HoverTarget2D(artist, hover_data))


def attach_hover(
    axes: Axes,
    hover_options: HoverOptions,
    hover_targets: list[_HoverTarget2D],
) -> None:
    """Attach a hover annotation overlay to the provided axes."""

    annotation = axes.annotate(
        "",
        xy=(0.0, 0.0),
        xycoords="figure pixels",
        xytext=(10.0, 10.0),
        textcoords="offset points",
        ha="left",
        va="bottom",
        fontsize=max(8.0, axes.figure.dpi / 12.0),
        color="#ffffff",
        zorder=_HOVER_ZORDER,
        annotation_clip=False,
        bbox={
            "boxstyle": "round,pad=0.18",
            "fc": "#222222",
            "ec": "#cccccc",
            "alpha": 0.9,
        },
    )
    annotation.set_visible(False)

    canvas = axes.figure.canvas
    if canvas is None:
        return

    def hide_annotation() -> None:
        if annotation.get_visible():
            annotation.set_visible(False)
            canvas.draw_idle()

    def on_motion(event: Event) -> None:
        if not isinstance(event, MouseEvent) or event.inaxes is not axes:
            hide_annotation()
            return

        for target in hover_targets:
            contains, _details = target.artist.contains(event)
            if not contains:
                continue
            visible_width, visible_height = visible_gate_size_pixels(axes, target.hover_data)
            hover_text = build_hover_text(
                target.hover_data,
                hover_options,
                visible_width,
                visible_height,
            )
            if not hover_text:
                hide_annotation()
                return
            annotation.xy = (event.x, event.y)
            annotation.set_text(hover_text)
            annotation.set_visible(True)
            canvas.draw_idle()
            return

        hide_annotation()

    callback_id = canvas.mpl_connect("motion_notify_event", on_motion)
    set_hover_state(axes, HoverState(annotation=annotation, callback_id=callback_id))


def build_hover_text(
    hover_data: SceneHoverData,
    hover_options: HoverOptions,
    visible_width: float,
    visible_height: float,
) -> str:
    """Build the hover annotation text for one scene element."""

    lines: list[str] = []
    if hover_options.show_name and hover_data.name:
        lines.append(hover_data.name)
    if hover_options.show_size:
        lines.append(f"size: {visible_width:.0f} x {visible_height:.0f} px")
    if hover_options.show_qubits and hover_data.wire_labels:
        lines.append(f"wires: {', '.join(hover_data.wire_labels)}")
    if should_show_matrix(hover_data, hover_options, visible_width, visible_height):
        lines.append(format_matrix(hover_data.matrix))
    return "\n".join(line for line in lines if line)


def should_show_matrix(
    hover_data: SceneHoverData,
    hover_options: HoverOptions,
    visible_width: float,
    visible_height: float,
) -> bool:
    """Return whether the hover should include matrix data."""

    if hover_options.show_matrix == "never" or hover_data.matrix is None:
        return False

    matrix = matrix_array(hover_data.matrix)
    if matrix is None:
        return False

    qubit_count = matrix_qubit_count(matrix)
    if qubit_count is None or qubit_count > hover_options.matrix_max_qubits:
        return False

    if hover_options.show_matrix == "always":
        return True

    return max(visible_width, visible_height) <= _SMALL_GATE_PIXEL_THRESHOLD


def visible_gate_size_pixels(axes: Axes, hover_data: SceneHoverData) -> tuple[float, float]:
    """Return the hovered gate size in display pixels."""

    x0, y0 = axes.transData.transform(
        (
            hover_data.gate_x - (hover_data.gate_width / 2.0),
            hover_data.gate_y - (hover_data.gate_height / 2.0),
        )
    )
    x1, y1 = axes.transData.transform(
        (
            hover_data.gate_x + (hover_data.gate_width / 2.0),
            hover_data.gate_y + (hover_data.gate_height / 2.0),
        )
    )
    return abs(float(x1 - x0)), abs(float(y1 - y0))


def format_matrix(matrix: object) -> str:
    """Format a square matrix for display inside hover annotations."""

    matrix_value = matrix_array(matrix)
    if matrix_value is None:
        return ""
    return np.array2string(
        matrix_value,
        separator=", ",
        formatter={"complex_kind": format_complex, "float_kind": format_complex},
    )


def matrix_array(matrix: object) -> np.ndarray | None:
    """Return a complex square matrix when the input can be represented as one."""

    try:
        matrix_value = np.asarray(matrix, dtype=np.complex128)
    except (TypeError, ValueError):
        return None
    if matrix_value.ndim != 2 or matrix_value.shape[0] != matrix_value.shape[1]:
        return None
    return matrix_value


def matrix_qubit_count(matrix: np.ndarray) -> int | None:
    """Return the number of qubits represented by a square unitary matrix."""

    dimension = int(matrix.shape[0])
    if dimension <= 0 or dimension & (dimension - 1):
        return None
    return int(np.log2(dimension))


def format_complex(value: object) -> str:
    """Format one matrix scalar in a compact human-readable form."""

    complex_value = _coerce_complex_scalar(value)
    if complex_value is None:
        return str(value)
    real = complex_value.real
    imag = complex_value.imag
    if abs(imag) < 5e-4:
        return f"{real:.3g}"
    if abs(real) < 5e-4:
        return f"{imag:.3g}j"
    sign = "+" if imag >= 0.0 else "-"
    return f"{real:.3g}{sign}{abs(imag):.3g}j"


def _coerce_complex_scalar(value: object) -> complex | None:
    try:
        scalar = np.asarray(value, dtype=np.complex128)
    except (TypeError, ValueError):
        return None
    if scalar.shape != ():
        return None
    return complex(np.complex128(scalar.item()))


def _set_hover_artist_extent(
    axes: Axes,
    artist: Artist,
    hover_data: SceneHoverData,
) -> None:
    renderer_getter = getattr(axes.figure.canvas, "get_renderer", None)
    if callable(renderer_getter):
        try:
            bounds = artist.get_window_extent(renderer=renderer_getter()).bounds
            if all(np.isfinite(bounds)):
                return
        except (AttributeError, RuntimeError, ValueError):
            pass

    def hover_extent(_artist: Artist, renderer: object = None) -> Bbox:
        return axes.transData.transform_bbox(
            Bbox.from_bounds(
                hover_data.gate_x - (hover_data.gate_width / 2.0),
                hover_data.gate_y - (hover_data.gate_height / 2.0),
                hover_data.gate_width,
                hover_data.gate_height,
            )
        )

    setattr(artist, "get_window_extent", MethodType(hover_extent, artist))
