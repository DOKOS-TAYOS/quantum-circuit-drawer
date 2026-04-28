"""Hover helpers for interactive 2D Matplotlib rendering."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import Event, MouseEvent

from ..hover import HoverOptions
from ..layout.scene import SceneHoverData
from ..style.theme import DrawTheme
from ..utils.matrix_support import matrix_qubit_count, square_matrix
from ._matplotlib_figure import HoverState, set_hover_state
from ._matplotlib_hover_position import position_hover_annotation

_HOVER_ZORDER = 10_000
_SMALL_GATE_PIXEL_THRESHOLD = 48.0


@dataclass(frozen=True, slots=True)
class _HoverTarget2D:
    hover_data: SceneHoverData
    x_min: float
    x_max: float
    y_min: float
    y_max: float


@dataclass(frozen=True, slots=True)
class _HoverBox2D:
    hover_data: SceneHoverData
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def area(self) -> float:
        return max(0.0, self.x_max - self.x_min) * max(0.0, self.y_max - self.y_min)


@dataclass(frozen=True, slots=True)
class _HoverGrid2D:
    hover_boxes: tuple[_HoverBox2D, ...]
    cell_size_x: float
    cell_size_y: float
    cells: dict[tuple[int, int], tuple[int, ...]]


def add_hover_target(
    hover_targets: list[_HoverTarget2D],
    hover_data: SceneHoverData,
    *,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    """Register one hoverable data-space box for later hover aggregation."""

    hover_targets.append(
        _HoverTarget2D(
            hover_data=hover_data,
            x_min=min(x_min, x_max),
            x_max=max(x_min, x_max),
            y_min=min(y_min, y_max),
            y_max=max(y_min, y_max),
        )
    )


def attach_hover(
    axes: Axes,
    hover_options: HoverOptions,
    hover_targets: list[_HoverTarget2D],
    *,
    theme: DrawTheme,
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
        color=theme.hover_text_color,
        zorder=_HOVER_ZORDER,
        annotation_clip=False,
        bbox={
            "boxstyle": "round,pad=0.18",
            "fc": theme.hover_facecolor,
            "ec": theme.hover_edgecolor,
            "alpha": 0.9,
        },
    )
    annotation.set_visible(False)

    canvas = axes.figure.canvas
    if canvas is None:
        return
    hover_boxes = _build_hover_boxes(hover_targets)
    hover_grid = _build_hover_grid(hover_boxes)
    active_hover_key: str | None = None

    def hide_annotation() -> None:
        nonlocal active_hover_key
        if annotation.get_visible():
            annotation.set_visible(False)
            active_hover_key = None
            canvas.draw_idle()

    def on_motion(event: Event) -> None:
        nonlocal active_hover_key
        if not isinstance(event, MouseEvent) or event.inaxes is not axes:
            hide_annotation()
            return

        if event.xdata is None or event.ydata is None:
            hide_annotation()
            return

        hover_box = _resolve_hover_box_in_grid(
            hover_grid,
            x=float(event.xdata),
            y=float(event.ydata),
        )
        if hover_box is None:
            hide_annotation()
            return

        if active_hover_key == hover_box.hover_data.key:
            return

        visible_width, visible_height = visible_gate_size_pixels(axes, hover_box.hover_data)
        hover_text = build_hover_text(
            hover_box.hover_data,
            hover_options,
            visible_width,
            visible_height,
        )
        if not hover_text:
            hide_annotation()
            return

        annotation.set_text(hover_text)
        position_hover_annotation(
            annotation,
            anchor_x=float(event.x),
            anchor_y=float(event.y),
        )
        annotation.set_visible(True)
        active_hover_key = hover_box.hover_data.key
        canvas.draw_idle()

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
    if hover_options.show_matrix_dimensions and hover_data.matrix_dimension is not None:
        lines.append(f"matrix: {hover_data.matrix_dimension} x {hover_data.matrix_dimension}")
    if hover_options.show_qubits and hover_data.qubit_labels:
        lines.append(f"qubits: {', '.join(hover_data.qubit_labels)}")
    if hover_options.show_qubits and hover_data.other_wire_labels:
        lines.append(f"bits: {', '.join(hover_data.other_wire_labels)}")
    lines.extend(detail for detail in hover_data.details if detail)
    if hover_options.show_size:
        lines.append(f"size: {visible_width:.0f} x {visible_height:.0f} px")
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

    matrix = square_matrix(hover_data.matrix)
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

    matrix_value = square_matrix(matrix)
    if matrix_value is None:
        return ""
    return np.array2string(
        matrix_value,
        separator=", ",
        formatter={"complex_kind": format_complex, "float_kind": format_complex},
    )


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


def _build_hover_boxes(
    hover_targets: list[_HoverTarget2D],
) -> tuple[_HoverBox2D, ...]:
    return tuple(_hover_box_from_target(target) for target in hover_targets)


def _build_hover_grid(hover_boxes: tuple[_HoverBox2D, ...]) -> _HoverGrid2D:
    if not hover_boxes:
        return _HoverGrid2D(
            hover_boxes=(),
            cell_size_x=1.0,
            cell_size_y=1.0,
            cells={},
        )

    widths = [
        hover_box.x_max - hover_box.x_min
        for hover_box in hover_boxes
        if hover_box.x_max > hover_box.x_min
    ]
    heights = [
        hover_box.y_max - hover_box.y_min
        for hover_box in hover_boxes
        if hover_box.y_max > hover_box.y_min
    ]
    x_min = min(hover_box.x_min for hover_box in hover_boxes)
    x_max = max(hover_box.x_max for hover_box in hover_boxes)
    y_min = min(hover_box.y_min for hover_box in hover_boxes)
    y_max = max(hover_box.y_max for hover_box in hover_boxes)
    span_x = max(1e-6, x_max - x_min)
    span_y = max(1e-6, y_max - y_min)
    cell_size_x = max(np.median(widths).item() if widths else span_x / 32.0, span_x / 64.0, 1e-6)
    cell_size_y = max(
        np.median(heights).item() if heights else span_y / 32.0,
        span_y / 64.0,
        1e-6,
    )
    cells: dict[tuple[int, int], list[int]] = {}
    for index, hover_box in enumerate(hover_boxes):
        x_start = floor(hover_box.x_min / cell_size_x)
        x_end = floor(hover_box.x_max / cell_size_x)
        y_start = floor(hover_box.y_min / cell_size_y)
        y_end = floor(hover_box.y_max / cell_size_y)
        for grid_x in range(x_start, x_end + 1):
            for grid_y in range(y_start, y_end + 1):
                cells.setdefault((grid_x, grid_y), []).append(index)
    return _HoverGrid2D(
        hover_boxes=hover_boxes,
        cell_size_x=float(cell_size_x),
        cell_size_y=float(cell_size_y),
        cells={cell: tuple(indexes) for cell, indexes in cells.items()},
    )


def _hover_box_from_target(
    target: _HoverTarget2D,
) -> _HoverBox2D:
    return _HoverBox2D(
        hover_data=target.hover_data,
        x_min=target.x_min,
        x_max=target.x_max,
        y_min=target.y_min,
        y_max=target.y_max,
    )


def _resolve_hover_box(
    hover_boxes: tuple[_HoverBox2D, ...],
    *,
    x: float,
    y: float,
) -> _HoverBox2D | None:
    matching_hover_boxes = [
        hover_box
        for hover_box in hover_boxes
        if hover_box.x_min <= x <= hover_box.x_max and hover_box.y_min <= y <= hover_box.y_max
    ]
    if not matching_hover_boxes:
        return None
    return min(matching_hover_boxes, key=lambda hover_box: hover_box.area)


def _resolve_hover_box_in_grid(
    hover_grid: _HoverGrid2D,
    *,
    x: float,
    y: float,
) -> _HoverBox2D | None:
    if not hover_grid.hover_boxes:
        return None

    grid_x = floor(x / hover_grid.cell_size_x)
    grid_y = floor(y / hover_grid.cell_size_y)
    candidate_indexes = hover_grid.cells.get((grid_x, grid_y), ())
    if not candidate_indexes:
        return None
    matching_hover_boxes = [
        hover_grid.hover_boxes[index]
        for index in candidate_indexes
        if hover_grid.hover_boxes[index].x_min <= x <= hover_grid.hover_boxes[index].x_max
        and hover_grid.hover_boxes[index].y_min <= y <= hover_grid.hover_boxes[index].y_max
    ]
    if not matching_hover_boxes:
        return None
    return min(matching_hover_boxes, key=lambda hover_box: hover_box.area)
