"""2D Matplotlib gate, measurement, and text drawing helpers."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

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
    SceneGroupHighlight,
    SceneMeasurement,
    SceneSwap,
    SceneText,
    SceneVisualState,
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
from ._matplotlib_visual_state import (
    alpha_for_visual_state,
    color_for_visual_state,
    gate_facecolor_for_visual_state,
    line_width_scale_for_visual_state,
    measurement_facecolor_for_visual_state,
)


@dataclass(frozen=True, slots=True)
class _PreparedGateText:
    text: str
    height_fraction: float
    is_stacked: bool


def _prepared_gate_text(gate: SceneGate, *, use_mathtext: bool) -> _PreparedGateText | None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        return None
    if gate.subtitle:
        return _PreparedGateText(
            text=format_gate_text_block(
                gate.label,
                gate.subtitle,
                use_mathtext=use_mathtext,
            ),
            height_fraction=_STACKED_TEXT_USABLE_HEIGHT_FRACTION,
            is_stacked=True,
        )
    return _PreparedGateText(
        text=format_visible_label(gate.label, use_mathtext=use_mathtext),
        height_fraction=_SINGLE_LINE_HEIGHT_FRACTION,
        is_stacked=False,
    )


def draw_group_highlights(
    ax: Axes,
    highlights: Sequence[SceneGroupHighlight],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> tuple[Patch, ...] | None:
    if not highlights:
        return None

    patches: list[Patch] = []
    for highlight in highlights:
        patch = FancyBboxPatch(
            (
                highlight.x + x_offset - (highlight.width / 2.0),
                highlight.y + y_offset - (highlight.height / 2.0),
            ),
            highlight.width,
            highlight.height,
            boxstyle="round,pad=0.03,rounding_size=0.08",
            facecolor=scene.style.theme.accent_color,
            edgecolor=scene.style.theme.accent_color,
            linewidth=1.0,
            zorder=OCCLUSION_LAYER_ZORDER - 1.0,
            alpha=0.08 * alpha_for_visual_state(highlight.visual_state),
        )
        patch.set_gid("decomposition-group-highlight")
        patches.append(_add_patch_artist(ax, patch))
    return tuple(patches)


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
        facecolor=gate_facecolor_for_visual_state(
            theme=scene.style.theme,
            visual_state=gate.visual_state,
        ),
        edgecolor=color_for_visual_state(
            scene.style.theme.gate_edgecolor,
            theme=scene.style.theme,
            visual_state=gate.visual_state,
        ),
        linewidth=resolved_gate_edge_line_width(scene.style)
        * line_width_scale_for_visual_state(gate.visual_state),
        zorder=OCCLUSION_LAYER_ZORDER,
        alpha=alpha_for_visual_state(gate.visual_state),
    )
    return _add_patch_artist(ax, patch)


def draw_x_target_circles(
    ax: Axes,
    gates: Sequence[SceneGate],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> tuple[EllipseCollection, ...] | None:
    collections: list[EllipseCollection] = []
    offsets_by_state: dict[SceneVisualState, list[tuple[float, float]]] = {}
    diameters_by_state: dict[SceneVisualState, list[float]] = {}
    for gate in gates:
        if gate.render_style is not GateRenderStyle.X_TARGET:
            continue
        offsets_by_state.setdefault(gate.visual_state, []).append(
            (gate.x + x_offset, gate.y + y_offset)
        )
        diameters_by_state.setdefault(gate.visual_state, []).append(
            min(gate.width, gate.height) * 0.72
        )

    for visual_state, offsets in offsets_by_state.items():
        collection = _add_ellipse_collection(
            ax,
            widths=diameters_by_state[visual_state],
            heights=diameters_by_state[visual_state],
            offsets=offsets,
            facecolor=scene.style.theme.axes_facecolor,
            edgecolor=color_for_visual_state(
                scene.style.theme.wire_color,
                theme=scene.style.theme,
                visual_state=visual_state,
            ),
            linewidth=resolved_gate_edge_line_width(scene.style)
            * line_width_scale_for_visual_state(visual_state),
            zorder=OCCLUSION_LAYER_ZORDER,
        )
        if collection is not None:
            collection.set_alpha(alpha_for_visual_state(visual_state))
            collections.append(collection)
    if not collections:
        return None
    return tuple(collections)


def draw_x_target_segments(
    ax: Axes,
    gates: Sequence[SceneGate],
    scene: LayoutScene,
    *,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
) -> tuple[LineCollection, ...] | None:
    if not gates:
        return None

    collections: list[LineCollection] = []
    segments_by_state: dict[
        SceneVisualState,
        list[tuple[tuple[float, float], tuple[float, float]]],
    ] = {}
    for gate in gates:
        if gate.render_style is not GateRenderStyle.X_TARGET:
            continue
        radius = min(gate.width, gate.height) * 0.36
        segments_by_state.setdefault(gate.visual_state, []).extend(
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

    for visual_state, segments in segments_by_state.items():
        collection = _add_line_collection(
            ax,
            segments,
            color=color_for_visual_state(
                scene.style.theme.wire_color,
                theme=scene.style.theme,
                visual_state=visual_state,
            ),
            linewidth=resolved_gate_edge_line_width(scene.style)
            * line_width_scale_for_visual_state(visual_state),
            zorder=SYMBOL_LAYER_ZORDER,
        )
        if collection is not None:
            collection.set_alpha(alpha_for_visual_state(visual_state))
            collections.append(collection)
    if not collections:
        return None
    return tuple(collections)


def draw_gate_label(
    ax: Axes,
    gate: SceneGate,
    scene: LayoutScene,
    *,
    label_font_size: float | None = None,
    prepared_text: _PreparedGateText | None = None,
    x_offset: float = 0.0,
    y_offset: float = 0.0,
    text_fit_context: _GateTextFittingContext | None = None,
    text_fit_cache: _GateTextCache | None = None,
) -> tuple[Text, Text | None] | None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        return None

    resolved_text = prepared_text or _prepared_gate_text(
        gate,
        use_mathtext=scene.style.use_mathtext,
    )
    if resolved_text is None:
        return None

    if resolved_text.is_stacked:
        resolved_label_font_size = label_font_size or _fit_gate_text_font_size(
            ax=ax,
            scene=scene,
            width=gate.width,
            height=gate.height,
            text=resolved_text.text,
            default_font_size=scene.style.font_size,
            height_fraction=resolved_text.height_fraction,
            context=text_fit_context,
            cache=text_fit_cache,
        )
        label_artist = _add_text_artist(
            ax,
            gate.x + x_offset,
            gate.y + y_offset,
            resolved_text.text,
            ha="center",
            va="center",
            multialignment="center",
            fontsize=resolved_label_font_size,
            linespacing=_multiline_text_line_spacing(resolved_label_font_size),
            color=color_for_visual_state(
                scene.style.theme.text_color,
                theme=scene.style.theme,
                visual_state=gate.visual_state,
            ),
            zorder=TEXT_LAYER_ZORDER,
            alpha=alpha_for_visual_state(gate.visual_state),
        )
        set_gate_text_metadata(
            label_artist,
            role="gate_label",
            gate_width=gate.width,
            gate_height=gate.height,
            height_fraction=resolved_text.height_fraction,
        )
        return label_artist, None

    resolved_label_font_size = label_font_size or _fit_gate_text_font_size(
        ax=ax,
        scene=scene,
        width=gate.width,
        height=gate.height,
        text=resolved_text.text,
        default_font_size=scene.style.font_size,
        height_fraction=resolved_text.height_fraction,
        context=text_fit_context,
        cache=text_fit_cache,
    )
    label_artist = _add_text_artist(
        ax,
        gate.x + x_offset,
        gate.y + y_offset,
        resolved_text.text,
        ha="center",
        va="center",
        fontsize=resolved_label_font_size,
        color=color_for_visual_state(
            scene.style.theme.text_color,
            theme=scene.style.theme,
            visual_state=gate.visual_state,
        ),
        zorder=TEXT_LAYER_ZORDER,
        alpha=alpha_for_visual_state(gate.visual_state),
    )
    set_gate_text_metadata(
        label_artist,
        role="gate_label",
        gate_width=gate.width,
        gate_height=gate.height,
        height_fraction=resolved_text.height_fraction,
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
    if not controls:
        return None

    diameter = scene.style.control_radius * 2
    control_color = scene.style.theme.control_color or scene.style.theme.wire_color
    closed_offsets_by_state: dict[SceneVisualState, list[tuple[float, float]]] = {}
    open_offsets_by_state: dict[SceneVisualState, list[tuple[float, float]]] = {}
    for control in controls:
        target = open_offsets_by_state if control.state == 0 else closed_offsets_by_state
        target.setdefault(control.visual_state, []).append(
            (control.x + x_offset, control.y + y_offset)
        )
    collections: list[EllipseCollection] = []
    for visual_state, closed_offsets in closed_offsets_by_state.items():
        closed_collection = _add_ellipse_collection(
            ax,
            widths=[diameter] * len(closed_offsets),
            heights=[diameter] * len(closed_offsets),
            offsets=closed_offsets,
            facecolor=color_for_visual_state(
                control_color,
                theme=scene.style.theme,
                visual_state=visual_state,
            ),
            edgecolor=color_for_visual_state(
                control_color,
                theme=scene.style.theme,
                visual_state=visual_state,
            ),
            linewidth=resolved_connection_line_width(scene.style)
            * line_width_scale_for_visual_state(visual_state),
            zorder=SYMBOL_LAYER_ZORDER,
        )
        if closed_collection is not None:
            closed_collection.set_alpha(alpha_for_visual_state(visual_state))
            collections.append(closed_collection)
    for visual_state, open_offsets in open_offsets_by_state.items():
        open_collection = _add_ellipse_collection(
            ax,
            widths=[diameter] * len(open_offsets),
            heights=[diameter] * len(open_offsets),
            offsets=open_offsets,
            facecolor=scene.style.theme.axes_facecolor,
            edgecolor=color_for_visual_state(
                control_color,
                theme=scene.style.theme,
                visual_state=visual_state,
            ),
            linewidth=resolved_connection_line_width(scene.style)
            * line_width_scale_for_visual_state(visual_state),
            zorder=SYMBOL_LAYER_ZORDER,
        )
        if open_collection is not None:
            open_collection.set_alpha(alpha_for_visual_state(visual_state))
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
) -> tuple[LineCollection, ...] | None:
    if not swaps:
        return None

    collections: list[LineCollection] = []
    segments_by_state: dict[
        SceneVisualState,
        list[tuple[tuple[float, float], tuple[float, float]]],
    ] = {}
    for swap in swaps:
        half = swap.marker_size
        for y in (swap.y_top + y_offset, swap.y_bottom + y_offset):
            segments_by_state.setdefault(swap.visual_state, []).extend(
                (
                    ((swap.x + x_offset - half, y - half), (swap.x + x_offset + half, y + half)),
                    ((swap.x + x_offset - half, y + half), (swap.x + x_offset + half, y - half)),
                )
            )

    for visual_state, segments in segments_by_state.items():
        collection = _add_line_collection(
            ax,
            segments,
            color=color_for_visual_state(
                scene.style.theme.wire_color,
                theme=scene.style.theme,
                visual_state=visual_state,
            ),
            linewidth=resolved_connection_line_width(scene.style)
            * line_width_scale_for_visual_state(visual_state),
            zorder=SYMBOL_LAYER_ZORDER,
        )
        if collection is not None:
            collection.set_alpha(alpha_for_visual_state(visual_state))
            collections.append(collection)
    if not collections:
        return None
    return tuple(collections)


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
        facecolor=measurement_facecolor_for_visual_state(
            theme=scene.style.theme,
            visual_state=measurement.visual_state,
        ),
        edgecolor=color_for_visual_state(
            scene.style.theme.measurement_color,
            theme=scene.style.theme,
            visual_state=measurement.visual_state,
        ),
        linewidth=resolved_measurement_line_width(scene.style)
        * line_width_scale_for_visual_state(measurement.visual_state),
        zorder=OCCLUSION_LAYER_ZORDER,
        alpha=alpha_for_visual_state(measurement.visual_state),
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
        color=color_for_visual_state(
            scene.style.theme.measurement_color,
            theme=scene.style.theme,
            visual_state=measurement.visual_state,
        ),
        linewidth=resolved_measurement_line_width(scene.style)
        * line_width_scale_for_visual_state(measurement.visual_state),
        zorder=SYMBOL_LAYER_ZORDER,
        alpha=alpha_for_visual_state(measurement.visual_state),
    )
    _add_patch_artist(ax, arc)
    ax.plot(
        [measurement_x - measurement.width * 0.05, measurement_x + measurement.width * 0.16],
        [
            measurement_y - measurement.height * 0.16,
            measurement_y + measurement.height * 0.14,
        ],
        color=color_for_visual_state(
            scene.style.theme.measurement_color,
            theme=scene.style.theme,
            visual_state=measurement.visual_state,
        ),
        linewidth=resolved_measurement_line_width(scene.style)
        * line_width_scale_for_visual_state(measurement.visual_state),
        solid_capstyle="round",
        zorder=SYMBOL_LAYER_ZORDER,
        clip_on=_axes_should_clip_artists(ax),
        alpha=alpha_for_visual_state(measurement.visual_state),
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
        color=color_for_visual_state(
            scene.style.theme.text_color,
            theme=scene.style.theme,
            visual_state=measurement.visual_state,
        ),
        zorder=TEXT_LAYER_ZORDER,
        alpha=alpha_for_visual_state(measurement.visual_state),
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
        color=color_for_visual_state(
            scene.style.theme.text_color,
            theme=scene.style.theme,
            visual_state=text.visual_state,
        ),
        zorder=TEXT_LAYER_ZORDER,
        alpha=alpha_for_visual_state(text.visual_state),
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
        color=color_for_visual_state(
            scene.style.theme.text_color,
            theme=scene.style.theme,
            visual_state=annotation.visual_state,
        ),
        zorder=TEXT_LAYER_ZORDER,
        alpha=alpha_for_visual_state(annotation.visual_state),
    )
    set_gate_text_metadata(
        annotation_artist,
        role="gate_annotation",
        gate_width=scene.style.gate_width * 0.5,
        gate_height=scene.style.gate_height * 0.5,
        height_fraction=1.0,
    )
