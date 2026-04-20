"""Reusable Matplotlib drawing primitives."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from types import MethodType
from typing import Any, cast

from matplotlib.axes import Axes
from matplotlib.collections import EllipseCollection, LineCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Arc, FancyArrowPatch, FancyBboxPatch, Patch
from matplotlib.text import Text
from matplotlib.textpath import TextPath
from matplotlib.transforms import Bbox

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
from ..style import (
    resolved_barrier_line_width,
    resolved_classical_wire_line_width,
    resolved_connection_line_width,
    resolved_gate_edge_line_width,
    resolved_measurement_line_width,
    resolved_wire_line_width,
)
from ..utils.formatting import format_gate_text_block, format_parameter_text, format_visible_label
from ._matplotlib_figure import get_viewport_width, set_gate_text_metadata

BASE_LAYER_ZORDER = 1
CONNECTION_LAYER_ZORDER = 2
OCCLUSION_LAYER_ZORDER = 4
SYMBOL_LAYER_ZORDER = 5
TEXT_LAYER_ZORDER = 6
LineSegment = tuple[tuple[float, float], tuple[float, float]]
_GateTextCacheKey = tuple[object, float, float]
_GateTextCache = dict[_GateTextCacheKey, float]
_SINGLE_LINE_HEIGHT_FRACTION = 0.62
_STACKED_TEXT_USABLE_HEIGHT_FRACTION = 0.72
_MULTILINE_TEXT_LINE_SPACING = 1.2
_MIN_GATE_TEXT_FONT_SIZE = 0.7
_MATHTEXT_WIDTH_PADDING_FACTOR = 1.25
_MATHTEXT_HEIGHT_PADDING_FACTOR = 1.1
_MEASUREMENT_LABEL_FONT_SCALE = 0.62
_MEASUREMENT_CLASSICAL_LABEL_FONT_SCALE = 0.56
_MEASUREMENT_CLASSICAL_LABEL_PATTERN = re.compile(r"^.+\[(\d+)\]$")
_GATE_TEXT_CONTEXT_CACHE_ATTR = "_quantum_circuit_drawer_gate_text_context_cache"
_NUMERIC_TEXT_PATTERN = re.compile(
    r"^[+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?(?:, [+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?)*$"
)
_SHAPE_METRICS_CACHE_SIZE = 256
_WINDOWED_CLIP_ATTR = "_quantum_circuit_drawer_windowed_clip"


@dataclass(frozen=True, slots=True)
class _GateTextFittingContext:
    default_scale: float
    points_per_layout_unit: float


@dataclass(frozen=True, slots=True)
class _ConnectionLabelStyle:
    text: str
    font_size: float
    bbox: Mapping[str, object]


def _measurement_half_gate_box(scene: LayoutScene) -> tuple[float, float]:
    return scene.style.gate_width * 0.5, scene.style.gate_height * 0.5


def _is_measurement_classical_connection_label(connection: SceneConnection) -> bool:
    return (
        connection.is_classical
        and connection.label is not None
        and not connection.double_line
        and connection.linestyle == "dashed"
    )


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
        _apply_axes_artist_clip(ax, patch)
        return patch

    children = cast(list[object], getattr(ax, "_children"))
    set_artist_props = cast(Any, getattr(ax, "_set_artist_props"))
    patch.axes = ax
    children.append(patch)
    setattr(patch, "_remove_method", children.remove)
    set_artist_props(patch)
    _apply_axes_artist_clip(ax, patch)
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
    clip_on = _axes_should_clip_artists(ax)
    if not _supports_fast_text_artist_path(ax):
        resolved_kwargs = dict(kwargs)
        resolved_kwargs.setdefault("clip_on", clip_on)
        if "fontsize" in resolved_kwargs and "fontproperties" not in resolved_kwargs:
            resolved_kwargs["fontproperties"] = _font_properties_for_size(
                float(resolved_kwargs.pop("fontsize"))
            )
        text_artist = ax.text(x, y, text, fontdict=fontdict_dict, **resolved_kwargs)
        _apply_axes_artist_clip(ax, text_artist)
        return text_artist

    effective_kwargs: dict[str, Any] = {
        "verticalalignment": "baseline",
        "horizontalalignment": "left",
        "transform": ax.transData,
        "clip_on": clip_on,
    }
    if fontdict_dict is not None:
        effective_kwargs.update(fontdict_dict)
    effective_kwargs.update(kwargs)
    if "fontsize" in effective_kwargs and "fontproperties" not in effective_kwargs:
        effective_kwargs["fontproperties"] = _font_properties_for_size(
            float(effective_kwargs.pop("fontsize"))
        )
    text_artist = Text(x=x, y=y, text=text, **effective_kwargs)
    add_text = cast(Any, getattr(ax, "_add_text"))
    added_text = cast(Text, add_text(text_artist))
    _apply_axes_artist_clip(ax, added_text)
    return added_text


def _add_line_collection(
    ax: Axes,
    segments: Sequence[LineSegment],
    *,
    color: str,
    linewidth: float,
    zorder: int,
    linestyle: str | tuple[int, tuple[int, int]] = "solid",
    capstyle: str = "round",
) -> LineCollection | None:
    if not segments:
        return None

    clip_on = _axes_should_clip_artists(ax)
    collection = LineCollection(
        segments,
        colors=color,
        linewidths=linewidth,
        linestyles=linestyle,
        capstyle=capstyle,
        zorder=zorder,
        clip_on=clip_on,
    )
    ax.add_collection(collection)
    _apply_axes_artist_clip(ax, collection)
    return collection


def _add_ellipse_collection(
    ax: Axes,
    *,
    widths: Sequence[float],
    heights: Sequence[float],
    offsets: Sequence[tuple[float, float]],
    facecolor: str,
    edgecolor: str,
    linewidth: float,
    zorder: int,
) -> EllipseCollection | None:
    if not offsets:
        return None

    clip_on = _axes_should_clip_artists(ax)
    collection = EllipseCollection(
        widths=widths,
        heights=heights,
        angles=[0.0] * len(offsets),
        units="xy",
        offsets=offsets,
        transOffset=ax.transData,
        facecolors=facecolor,
        edgecolors=edgecolor,
        linewidths=linewidth,
        zorder=zorder,
        clip_on=clip_on,
    )
    ax.add_collection(collection)
    _apply_axes_artist_clip(ax, collection)
    x_min = float("inf")
    x_max = float("-inf")
    y_min = float("inf")
    y_max = float("-inf")
    for (x, y), width, height in zip(offsets, widths, heights, strict=True):
        half_width = width / 2.0
        half_height = height / 2.0
        x_min = min(x_min, x - half_width)
        x_max = max(x_max, x + half_width)
        y_min = min(y_min, y - half_height)
        y_max = max(y_max, y + half_height)
    _set_artist_data_extent(
        ax,
        collection,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
    )
    return collection


def _set_artist_data_extent(
    ax: Axes,
    artist: object,
    *,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    def data_extent(_artist: object, renderer: object = None) -> Bbox:
        del renderer
        return ax.transData.transform_bbox(
            Bbox.from_extents(
                min(x_min, x_max),
                min(y_min, y_max),
                max(x_min, x_max),
                max(y_min, y_max),
            )
        )

    setattr(artist, "get_window_extent", MethodType(data_extent, artist))


def _axes_should_clip_artists(ax: Axes) -> bool:
    return bool(getattr(ax, _WINDOWED_CLIP_ATTR, False))


def _apply_axes_artist_clip(ax: Axes, artist: object) -> None:
    if not _axes_should_clip_artists(ax):
        return
    if hasattr(artist, "set_clip_on"):
        cast(Any, artist).set_clip_on(True)
    if hasattr(artist, "set_clip_path"):
        cast(Any, artist).set_clip_path(ax.patch)


@lru_cache(maxsize=32)
def _font_properties_for_size(font_size: float) -> FontProperties:
    return FontProperties(size=font_size)


@lru_cache(maxsize=1)
def _default_font_properties() -> FontProperties:
    return FontProperties()


def _fit_static_text_font_size(
    ax: Axes,
    scene: LayoutScene,
    *,
    text: str,
    default_font_size: float,
    available_width: float,
    available_height: float,
    context: _GateTextFittingContext | None = None,
    cache: _GateTextCache | None = None,
) -> float:
    resolved_context = context or _build_gate_text_fitting_context(ax, scene)
    return _fit_gate_text_font_size_with_context(
        context=resolved_context,
        width=available_width,
        height=available_height,
        text=text,
        default_font_size=default_font_size,
        height_fraction=1.0,
        max_font_size=default_font_size,
        cache={} if cache is None else cache,
    )


def _compact_measurement_classical_label(label: str) -> str | None:
    match = _MEASUREMENT_CLASSICAL_LABEL_PATTERN.match(label)
    if match is None:
        return None
    return f"[{match.group(1)}]"


def _connection_label_style(
    ax: Axes,
    connection: SceneConnection,
    scene: LayoutScene,
    label: str,
    *,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> _ConnectionLabelStyle:
    default_bbox: Mapping[str, object] = {
        "boxstyle": "round,pad=0.12,rounding_size=0.08",
        "facecolor": scene.style.theme.axes_facecolor,
        "edgecolor": "none",
    }
    if not _is_measurement_classical_connection_label(connection):
        return _ConnectionLabelStyle(
            text=format_visible_label(label, use_mathtext=scene.style.use_mathtext),
            font_size=scene.style.font_size * 0.7,
            bbox=default_bbox,
        )

    default_font_size = scene.style.font_size * _MEASUREMENT_CLASSICAL_LABEL_FONT_SCALE
    available_width, available_height = _measurement_half_gate_box(scene)
    visible_label = format_visible_label(label, use_mathtext=scene.style.use_mathtext)
    fitted_full_font_size = _fit_static_text_font_size(
        ax,
        scene,
        text=visible_label,
        default_font_size=default_font_size,
        available_width=available_width,
        available_height=available_height,
        context=text_fit_context,
        cache=text_fit_cache,
    )
    compact_label = _compact_measurement_classical_label(label)
    if compact_label is None or fitted_full_font_size >= default_font_size:
        return _ConnectionLabelStyle(
            text=visible_label,
            font_size=fitted_full_font_size,
            bbox={
                "boxstyle": "round,pad=0.06,rounding_size=0.06",
                "facecolor": scene.style.theme.axes_facecolor,
                "edgecolor": "none",
            },
        )

    visible_compact_label = format_visible_label(
        compact_label,
        use_mathtext=scene.style.use_mathtext,
    )
    compact_font_size = _fit_static_text_font_size(
        ax,
        scene,
        text=visible_compact_label,
        default_font_size=default_font_size,
        available_width=available_width,
        available_height=available_height,
        context=text_fit_context,
        cache=text_fit_cache,
    )
    return _ConnectionLabelStyle(
        text=visible_compact_label,
        font_size=compact_font_size,
        bbox={
            "boxstyle": "round,pad=0.05,rounding_size=0.05",
            "facecolor": scene.style.theme.axes_facecolor,
            "edgecolor": "none",
        },
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
    quantum_segments: list[LineSegment] = []
    classical_segments: list[LineSegment] = []
    classical_marker_segments: list[LineSegment] = []

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
    quantum_segments: list[LineSegment] = []
    classical_segments_by_style: dict[str | tuple[int, tuple[int, int]], list[LineSegment]] = {}
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
            label = connection.label
            label_style = _connection_label_style(
                ax,
                connection,
                scene,
                label,
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


def draw_gate_box(
    ax: Axes,
    gate: SceneGate,
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> Patch | None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        return None

    patch = FancyBboxPatch(
        (gate.x + x_offset - gate.width / 2, gate.y + y_offset - gate.height / 2),
        gate.width,
        gate.height,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        facecolor=scene.style.theme.gate_facecolor,
        edgecolor=scene.style.theme.gate_edgecolor,
        linewidth=resolved_gate_edge_line_width(scene.style),
        zorder=OCCLUSION_LAYER_ZORDER,
    )
    return _add_patch_artist(ax, patch)


def draw_x_target_circles(
    ax: Axes,
    gates: Sequence[SceneGate],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> EllipseCollection | None:
    offsets: list[tuple[float, float]] = []
    diameters: list[float] = []
    for gate in gates:
        if gate.render_style is not GateRenderStyle.X_TARGET:
            continue
        offsets.append((gate.x + x_offset, gate.y + y_offset))
        diameters.append(min(gate.width, gate.height) * 0.72)

    return _add_ellipse_collection(
        ax,
        widths=diameters,
        heights=diameters,
        offsets=offsets,
        facecolor=scene.style.theme.axes_facecolor,
        edgecolor=scene.style.theme.wire_color,
        linewidth=resolved_gate_edge_line_width(scene.style),
        zorder=OCCLUSION_LAYER_ZORDER,
    )


def draw_x_target_segments(
    ax: Axes,
    gates: Sequence[SceneGate],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> LineCollection | None:
    segments: list[LineSegment] = []
    for gate in gates:
        if gate.render_style is not GateRenderStyle.X_TARGET:
            continue
        radius = min(gate.width, gate.height) * 0.36
        segments.extend(
            (
                (
                    (gate.x + x_offset - radius, gate.y + y_offset),
                    (gate.x + x_offset + radius, gate.y + y_offset),
                ),
                (
                    (gate.x + x_offset, gate.y + y_offset - radius),
                    (gate.x + x_offset, gate.y + y_offset + radius),
                ),
            )
        )

    return _add_line_collection(
        ax,
        segments,
        color=scene.style.theme.wire_color,
        linewidth=resolved_gate_edge_line_width(scene.style),
        zorder=SYMBOL_LAYER_ZORDER,
    )


def draw_gate_label(
    ax: Axes,
    gate: SceneGate,
    scene: LayoutScene,
    *,
    label_font_size: float | None = None,
    subtitle_font_size: float | None = None,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> tuple[Text, Text | None] | None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        return None

    if gate.subtitle:
        visible_text = format_gate_text_block(
            gate.label,
            gate.subtitle,
            use_mathtext=scene.style.use_mathtext,
        )
        resolved_label_font_size = label_font_size or _fit_gate_text_font_size(
            ax=ax,
            scene=scene,
            width=gate.width,
            height=gate.height,
            text=visible_text,
            default_font_size=scene.style.font_size,
            height_fraction=_STACKED_TEXT_USABLE_HEIGHT_FRACTION,
            context=text_fit_context,
            cache=text_fit_cache,
        )
        label_artist = _add_text_artist(
            ax,
            gate.x + x_offset,
            gate.y + y_offset,
            visible_text,
            ha="center",
            va="center",
            multialignment="center",
            fontsize=resolved_label_font_size,
            linespacing=_multiline_text_line_spacing(resolved_label_font_size),
            color=scene.style.theme.text_color,
            zorder=TEXT_LAYER_ZORDER,
        )
        set_gate_text_metadata(
            label_artist,
            role="gate_label",
            gate_width=gate.width,
            gate_height=gate.height,
            height_fraction=_STACKED_TEXT_USABLE_HEIGHT_FRACTION,
        )
        return label_artist, None

    visible_label = format_visible_label(gate.label, use_mathtext=scene.style.use_mathtext)

    resolved_label_font_size = label_font_size or _fit_gate_text_font_size(
        ax=ax,
        scene=scene,
        width=gate.width,
        height=gate.height,
        text=visible_label,
        default_font_size=scene.style.font_size,
        height_fraction=_SINGLE_LINE_HEIGHT_FRACTION,
        context=text_fit_context,
        cache=text_fit_cache,
    )
    label_artist = _add_text_artist(
        ax,
        gate.x + x_offset,
        gate.y + y_offset,
        visible_label,
        ha="center",
        va="center",
        fontsize=resolved_label_font_size,
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )
    set_gate_text_metadata(
        label_artist,
        role="gate_label",
        gate_width=gate.width,
        gate_height=gate.height,
        height_fraction=_SINGLE_LINE_HEIGHT_FRACTION,
    )
    return label_artist, None


def draw_controls(
    ax: Axes,
    controls: Sequence[SceneControl],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> EllipseCollection | None:
    diameter = scene.style.control_radius * 2
    offsets = [(control.x + x_offset, control.y + y_offset) for control in controls]
    return _add_ellipse_collection(
        ax,
        widths=[diameter] * len(offsets),
        heights=[diameter] * len(offsets),
        offsets=offsets,
        facecolor=scene.style.theme.control_color or scene.style.theme.wire_color,
        edgecolor=scene.style.theme.control_color or scene.style.theme.wire_color,
        linewidth=resolved_connection_line_width(scene.style),
        zorder=SYMBOL_LAYER_ZORDER,
    )


def draw_swaps(
    ax: Axes,
    swaps: Sequence[SceneSwap],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> LineCollection | None:
    segments: list[LineSegment] = []
    for swap in swaps:
        half = swap.marker_size
        for y in (swap.y_top + y_offset, swap.y_bottom + y_offset):
            segments.extend(
                (
                    ((swap.x + x_offset - half, y - half), (swap.x + x_offset + half, y + half)),
                    ((swap.x + x_offset - half, y + half), (swap.x + x_offset + half, y - half)),
                )
            )

    return _add_line_collection(
        ax,
        segments,
        color=scene.style.theme.wire_color,
        linewidth=resolved_connection_line_width(scene.style),
        zorder=SYMBOL_LAYER_ZORDER,
    )


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


def draw_measurement_box(
    ax: Axes,
    measurement: SceneMeasurement,
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> Patch:
    patch = FancyBboxPatch(
        (
            measurement.x + x_offset - measurement.width / 2,
            measurement.quantum_y + y_offset - measurement.height / 2,
        ),
        measurement.width,
        measurement.height,
        boxstyle="round,pad=0.01,rounding_size=0.05",
        facecolor=scene.style.theme.measurement_facecolor,
        edgecolor=scene.style.theme.measurement_color,
        linewidth=resolved_measurement_line_width(scene.style),
        zorder=OCCLUSION_LAYER_ZORDER,
    )
    return _add_patch_artist(ax, patch)


def draw_measurement_symbol(
    ax: Axes,
    measurement: SceneMeasurement,
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> None:
    visible_label = format_visible_label(
        measurement.label,
        use_mathtext=scene.style.use_mathtext,
    )
    measurement_x = measurement.x + x_offset
    measurement_y = measurement.quantum_y + y_offset
    arc_center_y = measurement_y - measurement.height * 0.02
    arc = Arc(
        (measurement_x, arc_center_y),
        width=measurement.width * 0.58,
        height=measurement.height * 0.62,
        theta1=180,
        theta2=360,
        color=scene.style.theme.measurement_color,
        linewidth=resolved_measurement_line_width(scene.style),
        zorder=SYMBOL_LAYER_ZORDER,
    )
    _add_patch_artist(ax, arc)
    ax.plot(
        [measurement_x - measurement.width * 0.05, measurement_x + measurement.width * 0.16],
        [
            measurement_y - measurement.height * 0.16,
            measurement_y + measurement.height * 0.14,
        ],
        color=scene.style.theme.measurement_color,
        linewidth=resolved_measurement_line_width(scene.style),
        solid_capstyle="round",
        zorder=SYMBOL_LAYER_ZORDER,
        clip_on=_axes_should_clip_artists(ax),
    )
    for line in ax.lines[-1:]:
        _apply_axes_artist_clip(ax, line)
    measurement_label_artist = _add_text_artist(
        ax,
        measurement_x,
        measurement_y + measurement.height * 0.34,
        visible_label,
        ha="center",
        va="center",
        fontsize=_fit_static_text_font_size(
            ax,
            scene,
            text=visible_label,
            default_font_size=scene.style.font_size * _MEASUREMENT_LABEL_FONT_SCALE,
            available_width=measurement.width * 0.5,
            available_height=measurement.height * 0.5,
            context=text_fit_context,
            cache=text_fit_cache,
        ),
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )
    set_gate_text_metadata(
        measurement_label_artist,
        role="measurement_label",
        gate_width=measurement.width * 0.5,
        gate_height=measurement.height * 0.5,
        height_fraction=1.0,
    )


def draw_text(
    ax: Axes,
    text: SceneText,
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> None:
    visible_text = format_visible_label(text.text, use_mathtext=scene.style.use_mathtext)
    text_artist = _add_text_artist(
        ax,
        text.x + x_offset,
        text.y + y_offset,
        visible_text,
        ha=text.ha,
        va=text.va,
        fontsize=_fit_gate_text_font_size(
            ax=ax,
            scene=scene,
            width=scene.style.gate_width,
            height=scene.style.gate_height,
            text=visible_text,
            default_font_size=text.font_size or scene.style.font_size,
            height_fraction=_SINGLE_LINE_HEIGHT_FRACTION,
            context=text_fit_context,
            cache=text_fit_cache,
        ),
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )
    set_gate_text_metadata(
        text_artist,
        role="wire_label",
        gate_width=scene.style.gate_width,
        gate_height=scene.style.gate_height,
        height_fraction=_SINGLE_LINE_HEIGHT_FRACTION,
    )


def draw_gate_annotation(
    ax: Axes,
    annotation: SceneGateAnnotation,
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> None:
    visible_text = format_visible_label(
        annotation.text,
        use_mathtext=scene.style.use_mathtext,
    )
    annotation_artist = _add_text_artist(
        ax,
        annotation.x + x_offset,
        annotation.y + y_offset,
        visible_text,
        ha="left",
        va="center",
        fontsize=_fit_gate_text_font_size(
            ax=ax,
            scene=scene,
            width=scene.style.gate_width * 0.5,
            height=scene.style.gate_height * 0.5,
            text=visible_text,
            default_font_size=annotation.font_size,
            height_fraction=1.0,
            context=text_fit_context,
            cache=text_fit_cache,
        ),
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )
    set_gate_text_metadata(
        annotation_artist,
        role="gate_annotation",
        gate_width=scene.style.gate_width * 0.5,
        gate_height=scene.style.gate_height * 0.5,
        height_fraction=1.0,
    )


def _fit_gate_text_font_size(
    *,
    ax: Axes,
    scene: LayoutScene,
    width: float,
    height: float | None = None,
    text: str,
    default_font_size: float,
    height_fraction: float = _SINGLE_LINE_HEIGHT_FRACTION,
    max_font_size: float | None = None,
    context: _GateTextFittingContext | None = None,
    cache: _GateTextCache | None = None,
) -> float:
    """Shrink gate text when the rendered box is too narrow for the label."""

    resolved_context = context or _build_gate_text_fitting_context(ax, scene)
    return _fit_gate_text_font_size_with_context(
        context=resolved_context,
        width=width,
        height=height,
        text=text,
        default_font_size=default_font_size,
        height_fraction=height_fraction,
        max_font_size=max_font_size,
        cache={} if cache is None else cache,
    )


def _build_gate_text_fitting_context(ax: Axes, scene: LayoutScene) -> _GateTextFittingContext:
    effective_default_scale = _page_wrapped_font_scale(scene)
    axes_width_fraction = ax.get_position().width
    x_limits = ax.get_xlim()
    scene_width = abs(x_limits[1] - x_limits[0])
    figure = ax.figure
    canvas_width_pixels = (
        figure.canvas.get_width_height()[0]
        if figure.canvas is not None
        else figure.get_size_inches()[0] * figure.dpi
    )
    cache_key = (
        round(effective_default_scale, 9),
        round(axes_width_fraction, 9),
        round(x_limits[0], 9),
        round(x_limits[1], 9),
        round(scene_width, 9),
        int(round(canvas_width_pixels)),
        round(figure.dpi, 6),
    )
    cached_context = getattr(ax, _GATE_TEXT_CONTEXT_CACHE_ATTR, None)
    if (
        isinstance(cached_context, tuple)
        and len(cached_context) == 2
        and cached_context[0] == cache_key
        and isinstance(cached_context[1], _GateTextFittingContext)
    ):
        return cached_context[1]

    if axes_width_fraction <= 0.0 or scene_width <= 0.0:
        empty_context = _GateTextFittingContext(
            default_scale=effective_default_scale,
            points_per_layout_unit=0.0,
        )
        setattr(ax, _GATE_TEXT_CONTEXT_CACHE_ATTR, (cache_key, empty_context))
        return empty_context

    effective_scene_width = min(
        scene_width,
        get_viewport_width(figure, default=scene_width),
    )
    axes_width_points = (canvas_width_pixels * axes_width_fraction) * 72.0 / figure.dpi
    available_width_fraction = 0.74
    context = _GateTextFittingContext(
        default_scale=effective_default_scale,
        points_per_layout_unit=(axes_width_points * available_width_fraction)
        / effective_scene_width,
    )
    setattr(ax, _GATE_TEXT_CONTEXT_CACHE_ATTR, (cache_key, context))
    return context


def _fit_gate_text_font_size_with_context(
    *,
    context: _GateTextFittingContext,
    width: float,
    height: float | None = None,
    text: str,
    default_font_size: float,
    height_fraction: float = _SINGLE_LINE_HEIGHT_FRACTION,
    max_font_size: float | None = None,
    cache: _GateTextCache,
) -> float:
    """Shrink gate text using a per-page context and cache."""

    if not text:
        return default_font_size

    effective_default_font_size = (
        max_font_size if max_font_size is not None else default_font_size * context.default_scale
    )
    if context.points_per_layout_unit <= 0.0:
        return effective_default_font_size

    cache_text: object = _gate_text_fit_cache_token(text)
    if (
        height is not None
        or max_font_size is not None
        or abs(height_fraction - _SINGLE_LINE_HEIGHT_FRACTION) > 1e-9
    ):
        cache_text = (
            _gate_text_fit_cache_token(text),
            height,
            height_fraction,
            max_font_size,
        )
    cache_key = (cache_text, width, default_font_size)
    cached_font_size = cache.get(cache_key)
    if cached_font_size is not None:
        return cached_font_size

    available_width_points = context.points_per_layout_unit * width
    text_width_at_one_point = _text_width_in_points(text)
    if _is_mathtext_string(text):
        text_width_at_one_point *= _MATHTEXT_WIDTH_PADDING_FACTOR
    if text_width_at_one_point <= 0.0:
        cache[cache_key] = effective_default_font_size
        return effective_default_font_size

    fitted_font_size = available_width_points / text_width_at_one_point
    resolved_font_size = min(effective_default_font_size, fitted_font_size)
    if height is not None:
        available_height_points = context.points_per_layout_unit * height * height_fraction
        text_height_at_one_point = _text_height_in_points(
            text,
            line_spacing=_resolved_multiline_text_line_spacing(text, resolved_font_size),
        )
        if _is_mathtext_string(text):
            text_height_at_one_point *= _MATHTEXT_HEIGHT_PADDING_FACTOR
        if text_height_at_one_point > 0.0:
            resolved_font_size = min(
                resolved_font_size,
                available_height_points / text_height_at_one_point,
            )
            adjusted_text_height = _text_height_in_points(
                text,
                line_spacing=_resolved_multiline_text_line_spacing(text, resolved_font_size),
            )
            if _is_mathtext_string(text):
                adjusted_text_height *= _MATHTEXT_HEIGHT_PADDING_FACTOR
            if adjusted_text_height > 0.0:
                resolved_font_size = min(
                    resolved_font_size,
                    available_height_points / adjusted_text_height,
                )
    resolved_font_size = max(_MIN_GATE_TEXT_FONT_SIZE, resolved_font_size)
    cache[cache_key] = resolved_font_size
    return resolved_font_size


def _page_wrapped_font_scale(scene: LayoutScene) -> float:
    page_count = (
        scene.page_count_for_text_scale
        if scene.page_count_for_text_scale is not None
        else len(scene.pages)
    )
    if page_count <= 1:
        return 1.0
    return 0.9 * max(0.4, 1.0 - ((page_count - 2) * 0.035))


def _gate_text_fit_cache_token(text: str) -> object:
    shape_key = _text_shape_key(text)
    if shape_key is not None:
        return shape_key
    return text


def _is_mathtext_string(text: str) -> bool:
    if "\n" in text:
        text_lines = [line for line in text.split("\n") if line]
        return bool(text_lines) and all(_is_mathtext_string(line) for line in text_lines)
    return len(text) >= 2 and text.startswith("$") and text.endswith("$")


def _text_shape_key(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    if _NUMERIC_TEXT_PATTERN.fullmatch(text):
        return ("numeric", re.sub(r"\d", "0", text))
    return None


def _text_shape_sample(shape_key: tuple[str, str]) -> str:
    shape_kind, normalized_text = shape_key
    if shape_kind == "numeric":
        return normalized_text
    raise ValueError(f"unknown text shape kind: {shape_kind}")


@lru_cache(maxsize=_SHAPE_METRICS_CACHE_SIZE)
def _text_shape_metrics_in_points(shape_key: tuple[str, str]) -> tuple[float, float]:
    sample_text = _text_shape_sample(shape_key)
    extents = TextPath(
        (0.0, 0.0),
        sample_text,
        size=1.0,
        prop=_default_font_properties(),
    ).get_extents()
    return float(extents.width), float(extents.height)


@lru_cache(maxsize=128)
def _text_width_in_points(text: str) -> float:
    if "\n" in text:
        return max((_text_width_in_points(line) for line in text.split("\n")), default=0.0)
    shape_key = _text_shape_key(text)
    if shape_key is not None:
        return _text_shape_metrics_in_points(shape_key)[0]
    return TextPath((0.0, 0.0), text, size=1.0, prop=_default_font_properties()).get_extents().width


@lru_cache(maxsize=128)
def _text_height_in_points(
    text: str, *, line_spacing: float = _MULTILINE_TEXT_LINE_SPACING
) -> float:
    if "\n" in text:
        line_heights = [_text_height_in_points(line) for line in text.split("\n")]
        if not line_heights:
            return 0.0
        max_line_height = max(line_heights)
        extra_line_spacing = max(0.0, line_spacing - 1.0)
        return sum(line_heights) + (max_line_height * (len(line_heights) - 1) * extra_line_spacing)
    shape_key = _text_shape_key(text)
    if shape_key is not None:
        return _text_shape_metrics_in_points(shape_key)[1]
    return (
        TextPath((0.0, 0.0), text, size=1.0, prop=_default_font_properties()).get_extents().height
    )


def _multiline_text_line_spacing(font_size: float) -> float:
    if font_size <= 0.0:
        return 0.9
    normalized_font_size = min(1.0, font_size / 12.0)
    return 0.9 + ((_MULTILINE_TEXT_LINE_SPACING - 0.9) * normalized_font_size)


def _resolved_multiline_text_line_spacing(text: str, font_size: float) -> float:
    if "\n" not in text:
        return _MULTILINE_TEXT_LINE_SPACING
    return _multiline_text_line_spacing(font_size)


def finalize_axes(ax: Axes, scene: LayoutScene) -> None:
    ax.axis("off")
