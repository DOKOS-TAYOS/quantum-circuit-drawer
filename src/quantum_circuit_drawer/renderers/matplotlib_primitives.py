"""Reusable Matplotlib drawing primitives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Arc, Circle, FancyArrowPatch, FancyBboxPatch, Patch
from matplotlib.text import Text
from matplotlib.textpath import TextPath

from ..layout.scene import (
    GateRenderStyle,
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    SceneSwap,
    SceneText,
    SceneWire,
)
from ._matplotlib_figure import get_viewport_width

BASE_LAYER_ZORDER = 1
CONNECTION_LAYER_ZORDER = 2
OCCLUSION_LAYER_ZORDER = 4
SYMBOL_LAYER_ZORDER = 5
TEXT_LAYER_ZORDER = 6
LineSegment = tuple[tuple[float, float], tuple[float, float]]
_GateTextCacheKey = tuple[str, float, float]


@dataclass(frozen=True, slots=True)
class _GateTextFittingContext:
    default_scale: float
    points_per_layout_unit: float


def prepare_axes(ax: Axes, scene: LayoutScene) -> None:
    ax.set_xlim(0.0, scene.width)
    ax.set_ylim(scene.height, 0.0)
    ax.set_facecolor(scene.style.theme.axes_facecolor)
    ax.set_autoscale_on(False)
    ax.set_aspect("equal", adjustable="box")


def _supports_fast_patch_artist_path(ax: Axes) -> bool:
    return callable(getattr(ax, "_set_artist_props", None)) and isinstance(
        getattr(ax, "_children", None), list
    )


def _supports_fast_text_artist_path(ax: Axes) -> bool:
    return callable(getattr(ax, "_add_text", None))


def _add_patch_artist(ax: Axes, patch: Patch) -> Patch:
    if not _supports_fast_patch_artist_path(ax):
        ax.add_artist(patch)
        return patch

    children = cast(list[object], getattr(ax, "_children"))
    set_artist_props = cast(Any, getattr(ax, "_set_artist_props"))
    patch.axes = ax
    children.append(patch)
    setattr(patch, "_remove_method", children.remove)
    set_artist_props(patch)
    ax.stale = True
    return patch


def _add_text_artist(
    ax: Axes,
    x: float,
    y: float,
    text: str,
    fontdict: Mapping[str, Any] | None = None,
    **kwargs: Any,
) -> Text:
    fontdict_dict = dict(fontdict) if fontdict is not None else None
    if not _supports_fast_text_artist_path(ax):
        return ax.text(x, y, text, fontdict=fontdict_dict, **kwargs)

    effective_kwargs: dict[str, Any] = {
        "verticalalignment": "baseline",
        "horizontalalignment": "left",
        "transform": ax.transData,
        "clip_on": False,
    }
    if fontdict_dict is not None:
        effective_kwargs.update(fontdict_dict)
    effective_kwargs.update(kwargs)
    text_artist = Text(x=x, y=y, text=text, **effective_kwargs)
    add_text = cast(Any, getattr(ax, "_add_text"))
    return cast(Text, add_text(text_artist))


def _add_line_collection(
    ax: Axes,
    segments: Sequence[LineSegment],
    *,
    color: str,
    linewidth: float,
    zorder: int,
    linestyle: str | tuple[int, tuple[int, int]] = "solid",
    capstyle: str = "round",
) -> None:
    if not segments:
        return

    ax.add_collection(
        LineCollection(
            segments,
            colors=color,
            linewidths=linewidth,
            linestyles=linestyle,
            capstyle=capstyle,
            zorder=zorder,
            clip_on=False,
        )
    )


def draw_wires(ax: Axes, wires: Sequence[SceneWire], scene: LayoutScene) -> None:
    quantum_segments: list[LineSegment] = []
    classical_segments: list[LineSegment] = []
    classical_marker_segments: list[LineSegment] = []

    for wire in wires:
        if wire.kind.value == "classical":
            offset = max(0.025, scene.style.line_width * 0.01)
            classical_segments.extend(
                (
                    ((wire.x_start, wire.y - offset), (wire.x_end, wire.y - offset)),
                    ((wire.x_start, wire.y + offset), (wire.x_end, wire.y + offset)),
                )
            )
            marker_x = wire.x_start + 0.18
            classical_marker_segments.append(
                ((marker_x - 0.06, wire.y - 0.12), (marker_x + 0.06, wire.y + 0.12))
            )
            _add_text_artist(
                ax,
                marker_x,
                wire.y - 0.22,
                str(wire.bundle_size),
                ha="center",
                va="center",
                fontsize=scene.style.font_size * 0.66,
                color=scene.style.theme.classical_wire_color,
                zorder=TEXT_LAYER_ZORDER,
                bbox={
                    "boxstyle": "round,pad=0.08,rounding_size=0.05",
                    "facecolor": scene.style.theme.axes_facecolor,
                    "edgecolor": "none",
                },
            )
            continue

        quantum_segments.append(((wire.x_start, wire.y), (wire.x_end, wire.y)))

    _add_line_collection(
        ax,
        quantum_segments,
        color=scene.style.theme.wire_color,
        linewidth=scene.style.line_width,
        zorder=BASE_LAYER_ZORDER,
    )
    _add_line_collection(
        ax,
        classical_segments,
        color=scene.style.theme.classical_wire_color,
        linewidth=scene.style.line_width * 0.9,
        zorder=BASE_LAYER_ZORDER,
        capstyle="butt",
    )
    _add_line_collection(
        ax,
        classical_marker_segments,
        color=scene.style.theme.classical_wire_color,
        linewidth=scene.style.line_width * 0.9,
        zorder=SYMBOL_LAYER_ZORDER,
    )


def draw_wire(ax: Axes, wire: SceneWire, scene: LayoutScene) -> None:
    draw_wires(ax, (wire,), scene)


def draw_classical_wire(ax: Axes, wire: SceneWire, scene: LayoutScene) -> None:
    draw_wires(ax, (wire,), scene)


def draw_connections(ax: Axes, connections: Sequence[SceneConnection], scene: LayoutScene) -> None:
    quantum_segments: list[LineSegment] = []
    classical_segments_by_style: dict[str | tuple[int, tuple[int, int]], list[LineSegment]] = {}

    for connection in connections:
        line_end_y = connection.y_end
        if connection.arrow_at_end:
            direction = 1.0 if connection.y_end >= connection.y_start else -1.0
            arrow_length = max(0.12, scene.style.wire_spacing * 0.18)
            line_end_y = connection.y_end - (direction * arrow_length)

        if connection.is_classical and connection.double_line:
            offset = max(0.02, scene.style.line_width * 0.008)
            classical_segments = classical_segments_by_style.setdefault(connection.linestyle, [])
            classical_segments.extend(
                (
                    (
                        (connection.x - offset, connection.y_start),
                        (connection.x - offset, line_end_y),
                    ),
                    (
                        (connection.x + offset, connection.y_start),
                        (connection.x + offset, line_end_y),
                    ),
                )
            )
        else:
            segment = ((connection.x, connection.y_start), (connection.x, line_end_y))
            if connection.is_classical:
                classical_segments = classical_segments_by_style.setdefault(
                    connection.linestyle, []
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
                (connection.x, line_end_y),
                (connection.x, connection.y_end),
                arrowstyle="-|>",
                mutation_scale=10 + (scene.style.font_size * 0.45),
                linewidth=scene.style.line_width * 0.9,
                color=color,
                linestyle="solid",
                zorder=SYMBOL_LAYER_ZORDER,
            )
            _add_patch_artist(ax, arrow)
        if connection.label:
            label_y = (
                connection.y_start - 0.12
                if connection.is_classical and connection.double_line
                else None
            )
            if label_y is None:
                direction = 1.0 if connection.y_end >= connection.y_start else -1.0
                label_y = connection.y_end - (direction * 0.12)
            _add_text_artist(
                ax,
                connection.x + 0.12,
                label_y,
                connection.label,
                ha="left",
                va="center",
                fontsize=scene.style.font_size * 0.7,
                color=scene.style.theme.classical_wire_color
                if connection.is_classical
                else scene.style.theme.wire_color,
                zorder=TEXT_LAYER_ZORDER,
                bbox={
                    "boxstyle": "round,pad=0.12,rounding_size=0.08",
                    "facecolor": scene.style.theme.axes_facecolor,
                    "edgecolor": "none",
                },
            )

    _add_line_collection(
        ax,
        quantum_segments,
        color=scene.style.theme.wire_color,
        linewidth=scene.style.line_width,
        zorder=CONNECTION_LAYER_ZORDER,
        capstyle="butt",
    )
    for linestyle, classical_segments in classical_segments_by_style.items():
        _add_line_collection(
            ax,
            classical_segments,
            color=scene.style.theme.classical_wire_color,
            linewidth=scene.style.line_width,
            zorder=CONNECTION_LAYER_ZORDER,
            linestyle=linestyle,
            capstyle="butt",
        )


def draw_connection(ax: Axes, connection: SceneConnection, scene: LayoutScene) -> None:
    draw_connections(ax, (connection,), scene)


def draw_gate_box(ax: Axes, gate: SceneGate, scene: LayoutScene) -> None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        draw_x_target_circle(ax, gate, scene)
        return

    patch = FancyBboxPatch(
        (gate.x - gate.width / 2, gate.y - gate.height / 2),
        gate.width,
        gate.height,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        facecolor=scene.style.theme.gate_facecolor,
        edgecolor=scene.style.theme.gate_edgecolor,
        linewidth=scene.style.line_width,
        zorder=OCCLUSION_LAYER_ZORDER,
    )
    _add_patch_artist(ax, patch)


def draw_x_target_circle(ax: Axes, gate: SceneGate, scene: LayoutScene) -> None:
    radius = min(gate.width, gate.height) * 0.36
    _add_patch_artist(
        ax,
        Circle(
            (gate.x, gate.y),
            radius=radius,
            facecolor=scene.style.theme.axes_facecolor,
            edgecolor=scene.style.theme.wire_color,
            linewidth=scene.style.line_width,
            zorder=OCCLUSION_LAYER_ZORDER,
        ),
    )


def draw_x_target(ax: Axes, gate: SceneGate, scene: LayoutScene) -> None:
    draw_x_target_circle(ax, gate, scene)
    draw_x_target_segments(ax, (gate,), scene)


def draw_x_target_segments(ax: Axes, gates: Sequence[SceneGate], scene: LayoutScene) -> None:
    segments: list[LineSegment] = []
    for gate in gates:
        if gate.render_style is not GateRenderStyle.X_TARGET:
            continue
        radius = min(gate.width, gate.height) * 0.36
        segments.extend(
            (
                ((gate.x - radius, gate.y), (gate.x + radius, gate.y)),
                ((gate.x, gate.y - radius), (gate.x, gate.y + radius)),
            )
        )

    _add_line_collection(
        ax,
        segments,
        color=scene.style.theme.wire_color,
        linewidth=scene.style.line_width,
        zorder=SYMBOL_LAYER_ZORDER,
    )


def draw_gate_label(
    ax: Axes,
    gate: SceneGate,
    scene: LayoutScene,
    *,
    label_font_size: float | None = None,
    subtitle_font_size: float | None = None,
) -> None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        return

    resolved_label_font_size = label_font_size or _fit_gate_text_font_size(
        ax=ax,
        scene=scene,
        width=gate.width,
        text=gate.label,
        default_font_size=scene.style.font_size,
    )
    _add_text_artist(
        ax,
        gate.x,
        gate.y - 0.08 if gate.subtitle else gate.y,
        gate.label,
        ha="center",
        va="center",
        fontsize=resolved_label_font_size,
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )
    if gate.subtitle:
        resolved_subtitle_font_size = subtitle_font_size or _fit_gate_text_font_size(
            ax=ax,
            scene=scene,
            width=gate.width,
            text=gate.subtitle,
            default_font_size=scene.style.font_size * 0.78,
        )
        _add_text_artist(
            ax,
            gate.x,
            gate.y + 0.16,
            gate.subtitle,
            ha="center",
            va="center",
            fontsize=resolved_subtitle_font_size,
            color=scene.style.theme.text_color,
            zorder=TEXT_LAYER_ZORDER,
        )


def draw_control(ax: Axes, control: SceneControl, scene: LayoutScene) -> None:
    _add_patch_artist(
        ax,
        Circle(
            (control.x, control.y),
            radius=scene.style.control_radius,
            facecolor=scene.style.theme.wire_color,
            edgecolor=scene.style.theme.wire_color,
            linewidth=scene.style.line_width,
            zorder=SYMBOL_LAYER_ZORDER,
        ),
    )


def draw_swap(ax: Axes, swap: SceneSwap, scene: LayoutScene) -> None:
    draw_swaps(ax, (swap,), scene)


def draw_swaps(ax: Axes, swaps: Sequence[SceneSwap], scene: LayoutScene) -> None:
    segments: list[LineSegment] = []
    for swap in swaps:
        half = swap.marker_size
        for y in (swap.y_top, swap.y_bottom):
            segments.extend(
                (
                    ((swap.x - half, y - half), (swap.x + half, y + half)),
                    ((swap.x - half, y + half), (swap.x + half, y - half)),
                )
            )

    _add_line_collection(
        ax,
        segments,
        color=scene.style.theme.wire_color,
        linewidth=scene.style.line_width,
        zorder=SYMBOL_LAYER_ZORDER,
    )


def draw_barrier(ax: Axes, barrier: SceneBarrier, scene: LayoutScene) -> None:
    draw_barriers(ax, (barrier,), scene)


def draw_barriers(ax: Axes, barriers: Sequence[SceneBarrier], scene: LayoutScene) -> None:
    _add_line_collection(
        ax,
        [((barrier.x, barrier.y_top), (barrier.x, barrier.y_bottom)) for barrier in barriers],
        color=scene.style.theme.barrier_color,
        linewidth=scene.style.line_width,
        zorder=BASE_LAYER_ZORDER,
        linestyle=(0, (4, 2)),
        capstyle="butt",
    )


def draw_measurement_box(ax: Axes, measurement: SceneMeasurement, scene: LayoutScene) -> None:
    patch = FancyBboxPatch(
        (measurement.x - measurement.width / 2, measurement.quantum_y - measurement.height / 2),
        measurement.width,
        measurement.height,
        boxstyle="round,pad=0.01,rounding_size=0.05",
        facecolor=scene.style.theme.measurement_facecolor,
        edgecolor=scene.style.theme.measurement_color,
        linewidth=scene.style.line_width,
        zorder=OCCLUSION_LAYER_ZORDER,
    )
    _add_patch_artist(ax, patch)


def draw_measurement_symbol(ax: Axes, measurement: SceneMeasurement, scene: LayoutScene) -> None:
    arc_center_y = measurement.quantum_y - measurement.height * 0.02
    arc = Arc(
        (measurement.x, arc_center_y),
        width=measurement.width * 0.58,
        height=measurement.height * 0.62,
        theta1=180,
        theta2=360,
        color=scene.style.theme.measurement_color,
        linewidth=scene.style.line_width,
        zorder=SYMBOL_LAYER_ZORDER,
    )
    _add_patch_artist(ax, arc)
    ax.plot(
        [measurement.x - measurement.width * 0.05, measurement.x + measurement.width * 0.16],
        [
            measurement.quantum_y - measurement.height * 0.16,
            measurement.quantum_y + measurement.height * 0.14,
        ],
        color=scene.style.theme.measurement_color,
        linewidth=scene.style.line_width,
        solid_capstyle="round",
        zorder=SYMBOL_LAYER_ZORDER,
    )
    _add_text_artist(
        ax,
        measurement.x,
        measurement.quantum_y + measurement.height * 0.34,
        measurement.label,
        ha="center",
        va="center",
        fontsize=scene.style.font_size * 0.76,
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )


def draw_text(ax: Axes, text: SceneText, scene: LayoutScene) -> None:
    _add_text_artist(
        ax,
        text.x,
        text.y,
        text.text,
        ha=text.ha,
        va=text.va,
        fontsize=text.font_size or scene.style.font_size,
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )


def draw_gate_annotation(ax: Axes, annotation: SceneGateAnnotation, scene: LayoutScene) -> None:
    _add_text_artist(
        ax,
        annotation.x,
        annotation.y,
        annotation.text,
        ha="left",
        va="center",
        fontsize=annotation.font_size,
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )


def _fit_gate_text_font_size(
    *,
    ax: Axes,
    scene: LayoutScene,
    width: float,
    text: str,
    default_font_size: float,
) -> float:
    """Shrink gate text when the rendered box is too narrow for the label."""

    context = _build_gate_text_fitting_context(ax, scene)
    return _fit_gate_text_font_size_with_context(
        context=context,
        width=width,
        text=text,
        default_font_size=default_font_size,
        cache={},
    )


def _build_gate_text_fitting_context(ax: Axes, scene: LayoutScene) -> _GateTextFittingContext:
    effective_default_scale = _page_wrapped_font_scale(scene)
    axes_width_fraction = ax.get_position().width
    x_limits = ax.get_xlim()
    scene_width = abs(x_limits[1] - x_limits[0])
    if axes_width_fraction <= 0.0 or scene_width <= 0.0:
        return _GateTextFittingContext(
            default_scale=effective_default_scale,
            points_per_layout_unit=0.0,
        )

    figure = ax.figure
    canvas_width_pixels = (
        figure.canvas.get_width_height()[0]
        if figure.canvas is not None
        else figure.get_size_inches()[0] * figure.dpi
    )
    effective_scene_width = min(
        scene_width,
        get_viewport_width(figure, default=scene_width),
    )
    axes_width_points = (canvas_width_pixels * axes_width_fraction) * 72.0 / figure.dpi
    available_width_fraction = 0.74
    return _GateTextFittingContext(
        default_scale=effective_default_scale,
        points_per_layout_unit=(axes_width_points * available_width_fraction)
        / effective_scene_width,
    )


def _fit_gate_text_font_size_with_context(
    *,
    context: _GateTextFittingContext,
    width: float,
    text: str,
    default_font_size: float,
    cache: dict[_GateTextCacheKey, float],
) -> float:
    """Shrink gate text using a per-page context and cache."""

    if not text:
        return default_font_size

    effective_default_font_size = default_font_size * context.default_scale
    if context.points_per_layout_unit <= 0.0:
        return effective_default_font_size

    cache_key = (text, width, default_font_size)
    cached_font_size = cache.get(cache_key)
    if cached_font_size is not None:
        return cached_font_size

    available_width_points = context.points_per_layout_unit * width
    text_width_at_one_point = _text_width_in_points(text)
    if text_width_at_one_point <= 0.0:
        cache[cache_key] = effective_default_font_size
        return effective_default_font_size

    fitted_font_size = available_width_points / text_width_at_one_point
    resolved_font_size = max(3.5, min(effective_default_font_size, fitted_font_size))
    cache[cache_key] = resolved_font_size
    return resolved_font_size


def _page_wrapped_font_scale(scene: LayoutScene) -> float:
    page_count = len(scene.pages)
    if page_count <= 1:
        return 1.0
    return 0.9 * max(0.4, 1.0 - ((page_count - 2) * 0.035))


@lru_cache(maxsize=128)
def _text_width_in_points(text: str) -> float:
    return TextPath((0.0, 0.0), text, size=1.0, prop=FontProperties()).get_extents().width


def finalize_axes(ax: Axes, scene: LayoutScene) -> None:
    ax.axis("off")
