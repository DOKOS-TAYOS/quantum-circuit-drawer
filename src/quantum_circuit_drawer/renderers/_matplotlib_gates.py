"""2D Matplotlib gate, measurement, and text drawing helpers."""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib.axes import Axes
from matplotlib.collections import EllipseCollection, LineCollection
from matplotlib.patches import Arc, FancyBboxPatch, Patch
from matplotlib.text import Text

from ..layout.scene import (
    GateRenderStyle,
    LayoutScene,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    SceneSwap,
    SceneText,
)
from ..style import (
    resolved_connection_line_width,
    resolved_gate_edge_line_width,
    resolved_measurement_line_width,
)
from ..utils.formatting import format_gate_text_block, format_visible_label
from ._matplotlib_axes import (
    OCCLUSION_LAYER_ZORDER,
    SYMBOL_LAYER_ZORDER,
    TEXT_LAYER_ZORDER,
    _add_ellipse_collection,
    _add_line_collection,
    _add_patch_artist,
    _add_text_artist,
    _apply_axes_artist_clip,
    _axes_should_clip_artists,
)
from ._matplotlib_figure import set_gate_text_metadata
from ._matplotlib_text import (
    _MEASUREMENT_LABEL_FONT_SCALE,
    _SINGLE_LINE_HEIGHT_FRACTION,
    _STACKED_TEXT_USABLE_HEIGHT_FRACTION,
    _fit_gate_text_font_size,
    _fit_static_text_font_size,
    _GateTextCache,
    _GateTextFittingContext,
    _multiline_text_line_spacing,
)


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
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
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
) -> tuple[EllipseCollection, ...] | None:
    diameter = scene.style.control_radius * 2
    control_color = scene.style.theme.control_color or scene.style.theme.wire_color
    closed_offsets = [
        (control.x + x_offset, control.y + y_offset) for control in controls if control.state != 0
    ]
    open_offsets = [
        (control.x + x_offset, control.y + y_offset) for control in controls if control.state == 0
    ]
    collections: list[EllipseCollection] = []
    closed_collection = _add_ellipse_collection(
        ax,
        widths=[diameter] * len(closed_offsets),
        heights=[diameter] * len(closed_offsets),
        offsets=closed_offsets,
        facecolor=control_color,
        edgecolor=control_color,
        linewidth=resolved_connection_line_width(scene.style),
        zorder=SYMBOL_LAYER_ZORDER,
    )
    if closed_collection is not None:
        collections.append(closed_collection)
    open_collection = _add_ellipse_collection(
        ax,
        widths=[diameter] * len(open_offsets),
        heights=[diameter] * len(open_offsets),
        offsets=open_offsets,
        facecolor=scene.style.theme.axes_facecolor,
        edgecolor=control_color,
        linewidth=resolved_connection_line_width(scene.style),
        zorder=SYMBOL_LAYER_ZORDER,
    )
    if open_collection is not None:
        collections.append(open_collection)
    if not collections:
        return None
    return tuple(collections)


def draw_swaps(
    ax: Axes,
    swaps: Sequence[SceneSwap],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> LineCollection | None:
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
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
