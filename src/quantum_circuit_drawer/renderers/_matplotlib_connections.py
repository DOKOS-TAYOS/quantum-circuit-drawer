"""2D Matplotlib connection and wire drawing helpers."""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.patches import FancyArrowPatch

from ..layout.scene import LayoutScene, SceneBarrier, SceneConnection, SceneWire
from ..style import (
    resolved_barrier_line_width,
    resolved_classical_wire_line_width,
    resolved_connection_line_width,
    resolved_wire_line_width,
)
from ..utils.formatting import format_parameter_text
from ._matplotlib_axes import (
    BASE_LAYER_ZORDER,
    CONNECTION_LAYER_ZORDER,
    SYMBOL_LAYER_ZORDER,
    TEXT_LAYER_ZORDER,
    _add_line_collection,
    _add_patch_artist,
    _add_text_artist,
)
from ._matplotlib_figure import set_gate_text_metadata
from ._matplotlib_text import (
    _connection_label_style,
    _fit_gate_text_font_size,
    _GateTextCache,
    _GateTextFittingContext,
    _is_measurement_classical_connection_label,
    _measurement_half_gate_box,
)


def draw_wires(
    ax: Axes,
    wires: Sequence[SceneWire],
    scene: LayoutScene,
    *,
    y_offset: float = 0.0,
    x_start: float | None = None,
    x_end: float | None = None,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> None:
    quantum_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    classical_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    classical_marker_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []

    for wire in wires:
        wire_y = wire.y + y_offset
        wire_x_start = x_start if x_start is not None else wire.x_start
        wire_x_end = x_end if x_end is not None else wire.x_end
        if wire.kind.value == "classical":
            offset = max(0.025, resolved_classical_wire_line_width(scene.style) * 0.01)
            classical_segments.extend(
                (
                    ((wire_x_start, wire_y - offset), (wire_x_end, wire_y - offset)),
                    ((wire_x_start, wire_y + offset), (wire_x_end, wire_y + offset)),
                )
            )
            marker_x = wire_x_start + 0.18
            classical_marker_segments.append(
                ((marker_x - 0.06, wire_y - 0.12), (marker_x + 0.06, wire_y + 0.12))
            )
            bundle_text = format_parameter_text(
                str(wire.bundle_size),
                use_mathtext=scene.style.use_mathtext,
            )
            classical_bundle_text = _add_text_artist(
                ax,
                marker_x,
                wire_y - 0.22,
                bundle_text,
                ha="center",
                va="center",
                fontsize=_fit_gate_text_font_size(
                    ax=ax,
                    scene=scene,
                    width=scene.style.gate_width * 0.5,
                    height=scene.style.gate_height * 0.5,
                    text=bundle_text,
                    default_font_size=scene.style.font_size * 0.66,
                    height_fraction=1.0,
                    context=text_fit_context,
                    cache=text_fit_cache,
                ),
                color=scene.style.theme.classical_wire_color,
                zorder=TEXT_LAYER_ZORDER,
                bbox={
                    "boxstyle": "round,pad=0.08,rounding_size=0.05",
                    "facecolor": scene.style.theme.axes_facecolor,
                    "edgecolor": "none",
                },
            )
            set_gate_text_metadata(
                classical_bundle_text,
                role="classical_bundle_size",
                gate_width=scene.style.gate_width * 0.5,
                gate_height=scene.style.gate_height * 0.5,
                height_fraction=1.0,
            )
            continue

        quantum_segments.append(((wire_x_start, wire_y), (wire_x_end, wire_y)))

    _add_line_collection(
        ax,
        quantum_segments,
        color=scene.style.theme.wire_color,
        linewidth=resolved_wire_line_width(scene.style),
        zorder=BASE_LAYER_ZORDER,
    )
    _add_line_collection(
        ax,
        classical_segments,
        color=scene.style.theme.classical_wire_color,
        linewidth=resolved_classical_wire_line_width(scene.style),
        zorder=BASE_LAYER_ZORDER,
        capstyle="butt",
    )
    _add_line_collection(
        ax,
        classical_marker_segments,
        color=scene.style.theme.classical_wire_color,
        linewidth=resolved_classical_wire_line_width(scene.style),
        zorder=SYMBOL_LAYER_ZORDER,
    )


def draw_connections(
    ax: Axes,
    connections: Sequence[SceneConnection],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> list[object]:
    quantum_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    classical_segments_by_style: dict[
        str | tuple[int, tuple[int, int]], list[tuple[tuple[float, float], tuple[float, float]]]
    ] = {}
    artists: list[object] = []

    for connection in connections:
        connection_x = connection.x + x_offset
        connection_y_start = connection.y_start + y_offset
        connection_y_end = connection.y_end + y_offset
        line_end_y = connection_y_end
        if connection.arrow_at_end:
            direction = 1.0 if connection_y_end >= connection_y_start else -1.0
            arrow_length = max(0.12, scene.style.wire_spacing * 0.18)
            line_end_y = connection_y_end - (direction * arrow_length)

        if connection.is_classical and connection.double_line:
            offset = max(0.02, resolved_classical_wire_line_width(scene.style) * 0.008)
            classical_segments = classical_segments_by_style.setdefault(connection.linestyle, [])
            classical_segments.extend(
                (
                    (
                        (connection_x - offset, connection_y_start),
                        (connection_x - offset, line_end_y),
                    ),
                    (
                        (connection_x + offset, connection_y_start),
                        (connection_x + offset, line_end_y),
                    ),
                )
            )
        else:
            segment = ((connection_x, connection_y_start), (connection_x, line_end_y))
            if connection.is_classical:
                classical_segments = classical_segments_by_style.setdefault(
                    connection.linestyle,
                    [],
                )
                classical_segments.append(segment)
            else:
                quantum_segments.append(segment)

        if connection.arrow_at_end:
            color = (
                scene.style.theme.classical_wire_color
                if connection.is_classical
                else scene.style.theme.wire_color
            )
            arrow = FancyArrowPatch(
                (connection_x, line_end_y),
                (connection_x, connection_y_end),
                arrowstyle="-|>",
                mutation_scale=10 + (scene.style.font_size * 0.45),
                linewidth=resolved_connection_line_width(scene.style),
                color=color,
                linestyle="solid",
                zorder=SYMBOL_LAYER_ZORDER,
            )
            artists.append(_add_patch_artist(ax, arrow))
        if connection.label:
            label_y = (
                connection_y_start - 0.12
                if connection.is_classical and connection.double_line
                else None
            )
            if label_y is None:
                direction = 1.0 if connection_y_end >= connection_y_start else -1.0
                label_y = connection_y_end - (direction * 0.12)
            label_style = _connection_label_style(
                ax,
                connection,
                scene,
                connection.label,
                text_fit_context=text_fit_context,
                text_fit_cache=text_fit_cache,
            )
            label_artist = _add_text_artist(
                ax,
                connection_x + 0.12,
                label_y,
                label_style.text,
                ha="left",
                va="center",
                fontsize=label_style.font_size,
                color=scene.style.theme.classical_wire_color
                if connection.is_classical
                else scene.style.theme.wire_color,
                zorder=TEXT_LAYER_ZORDER,
                bbox=label_style.bbox,
            )
            if _is_measurement_classical_connection_label(connection):
                label_width, label_height = _measurement_half_gate_box(scene)
                set_gate_text_metadata(
                    label_artist,
                    role="measurement_classical_label",
                    gate_width=label_width,
                    gate_height=label_height,
                    height_fraction=1.0,
                )

    quantum_collection = _add_line_collection(
        ax,
        quantum_segments,
        color=scene.style.theme.wire_color,
        linewidth=resolved_connection_line_width(scene.style),
        zorder=CONNECTION_LAYER_ZORDER,
        capstyle="butt",
    )
    if quantum_collection is not None:
        artists.append(quantum_collection)
    for linestyle, classical_segments in classical_segments_by_style.items():
        classical_collection = _add_line_collection(
            ax,
            classical_segments,
            color=scene.style.theme.classical_wire_color,
            linewidth=resolved_classical_wire_line_width(scene.style),
            zorder=CONNECTION_LAYER_ZORDER,
            linestyle=linestyle,
            capstyle="butt",
        )
        if classical_collection is not None:
            artists.append(classical_collection)
    return artists


def draw_barriers(
    ax: Axes,
    barriers: Sequence[SceneBarrier],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> None:
    _add_line_collection(
        ax,
        [
            (
                (barrier.x + x_offset, barrier.y_top + y_offset),
                (barrier.x + x_offset, barrier.y_bottom + y_offset),
            )
            for barrier in barriers
        ],
        color=scene.style.theme.barrier_color,
        linewidth=resolved_barrier_line_width(scene.style),
        zorder=BASE_LAYER_ZORDER,
        linestyle=(0, (4, 2)),
        capstyle="butt",
    )
