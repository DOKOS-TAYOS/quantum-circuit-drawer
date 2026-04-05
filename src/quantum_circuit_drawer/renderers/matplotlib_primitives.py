"""Reusable Matplotlib drawing primitives."""

from __future__ import annotations

from functools import lru_cache

from matplotlib.axes import Axes
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Arc, Circle, FancyArrowPatch, FancyBboxPatch, Patch
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


def prepare_axes(ax: Axes, scene: LayoutScene) -> None:
    ax.set_xlim(0.0, scene.width)
    ax.set_ylim(scene.height, 0.0)
    ax.set_facecolor(scene.style.theme.axes_facecolor)
    ax.set_autoscale_on(False)
    ax.set_aspect("equal", adjustable="box")


def _add_patch_artist(ax: Axes, patch: Patch) -> None:
    ax.add_artist(patch)


def draw_wire(ax: Axes, wire: SceneWire, scene: LayoutScene) -> None:
    if wire.kind.value == "classical":
        draw_classical_wire(ax, wire, scene)
        return

    ax.plot(
        [wire.x_start, wire.x_end],
        [wire.y, wire.y],
        color=scene.style.theme.wire_color,
        linewidth=scene.style.line_width,
        solid_capstyle="round",
        zorder=BASE_LAYER_ZORDER,
    )


def draw_classical_wire(ax: Axes, wire: SceneWire, scene: LayoutScene) -> None:
    color = scene.style.theme.classical_wire_color
    offset = max(0.025, scene.style.line_width * 0.01)
    for y in (wire.y - offset, wire.y + offset):
        ax.plot(
            [wire.x_start, wire.x_end],
            [y, y],
            color=color,
            linewidth=scene.style.line_width * 0.9,
            solid_capstyle="butt",
            zorder=BASE_LAYER_ZORDER,
        )

    marker_x = wire.x_start + 0.18
    ax.plot(
        [marker_x - 0.06, marker_x + 0.06],
        [wire.y - 0.12, wire.y + 0.12],
        color=color,
        linewidth=scene.style.line_width * 0.9,
        solid_capstyle="round",
        zorder=SYMBOL_LAYER_ZORDER,
    )
    ax.text(
        marker_x,
        wire.y - 0.22,
        str(wire.bundle_size),
        ha="center",
        va="center",
        fontsize=scene.style.font_size * 0.66,
        color=color,
        zorder=TEXT_LAYER_ZORDER,
        bbox={
            "boxstyle": "round,pad=0.08,rounding_size=0.05",
            "facecolor": scene.style.theme.axes_facecolor,
            "edgecolor": "none",
        },
    )


def draw_connection(ax: Axes, connection: SceneConnection, scene: LayoutScene) -> None:
    color = (
        scene.style.theme.classical_wire_color
        if connection.is_classical
        else scene.style.theme.wire_color
    )
    linestyle: str | tuple[int, tuple[int, int]]
    linestyle = (0, (3, 2)) if connection.linestyle == "dashed" else "-"
    line_end_y = connection.y_end
    if connection.arrow_at_end:
        direction = 1.0 if connection.y_end >= connection.y_start else -1.0
        arrow_length = max(0.12, scene.style.wire_spacing * 0.18)
        line_end_y = connection.y_end - (direction * arrow_length)
    ax.plot(
        [connection.x, connection.x],
        [connection.y_start, line_end_y],
        color=color,
        linewidth=scene.style.line_width,
        linestyle=linestyle,
        dash_capstyle="butt",
        solid_capstyle="butt",
        zorder=CONNECTION_LAYER_ZORDER,
    )
    if connection.arrow_at_end:
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
        direction = 1.0 if connection.y_end >= connection.y_start else -1.0
        ax.text(
            connection.x + 0.12,
            connection.y_end - (direction * 0.12),
            connection.label,
            ha="left",
            va="center",
            fontsize=scene.style.font_size * 0.7,
            color=color,
            zorder=TEXT_LAYER_ZORDER,
            bbox={
                "boxstyle": "round,pad=0.12,rounding_size=0.08",
                "facecolor": scene.style.theme.axes_facecolor,
                "edgecolor": "none",
            },
        )


def draw_gate_box(ax: Axes, gate: SceneGate, scene: LayoutScene) -> None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        draw_x_target(ax, gate, scene)
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


def draw_x_target(ax: Axes, gate: SceneGate, scene: LayoutScene) -> None:
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
    ax.plot(
        [gate.x - radius, gate.x + radius],
        [gate.y, gate.y],
        color=scene.style.theme.wire_color,
        linewidth=scene.style.line_width,
        solid_capstyle="round",
        zorder=SYMBOL_LAYER_ZORDER,
    )
    ax.plot(
        [gate.x, gate.x],
        [gate.y - radius, gate.y + radius],
        color=scene.style.theme.wire_color,
        linewidth=scene.style.line_width,
        solid_capstyle="round",
        zorder=SYMBOL_LAYER_ZORDER,
    )


def draw_gate_label(ax: Axes, gate: SceneGate, scene: LayoutScene) -> None:
    if gate.render_style is GateRenderStyle.X_TARGET:
        return

    label_font_size = _fit_gate_text_font_size(
        ax=ax,
        scene=scene,
        width=gate.width,
        text=gate.label,
        default_font_size=scene.style.font_size,
    )
    ax.text(
        gate.x,
        gate.y - 0.08 if gate.subtitle else gate.y,
        gate.label,
        ha="center",
        va="center",
        fontsize=label_font_size,
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )
    if gate.subtitle:
        subtitle_font_size = _fit_gate_text_font_size(
            ax=ax,
            scene=scene,
            width=gate.width,
            text=gate.subtitle,
            default_font_size=scene.style.font_size * 0.78,
        )
        ax.text(
            gate.x,
            gate.y + 0.16,
            gate.subtitle,
            ha="center",
            va="center",
            fontsize=subtitle_font_size,
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
    half = swap.marker_size
    for y in (swap.y_top, swap.y_bottom):
        ax.plot(
            [swap.x - half, swap.x + half],
            [y - half, y + half],
            color=scene.style.theme.wire_color,
            linewidth=scene.style.line_width,
            solid_capstyle="round",
            zorder=SYMBOL_LAYER_ZORDER,
        )
        ax.plot(
            [swap.x - half, swap.x + half],
            [y + half, y - half],
            color=scene.style.theme.wire_color,
            linewidth=scene.style.line_width,
            solid_capstyle="round",
            zorder=SYMBOL_LAYER_ZORDER,
        )


def draw_barrier(ax: Axes, barrier: SceneBarrier, scene: LayoutScene) -> None:
    ax.plot(
        [barrier.x, barrier.x],
        [barrier.y_top, barrier.y_bottom],
        color=scene.style.theme.barrier_color,
        linewidth=scene.style.line_width,
        linestyle=(0, (4, 2)),
        dash_capstyle="butt",
        zorder=BASE_LAYER_ZORDER,
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
    ax.text(
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
    ax.text(
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
    ax.text(
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

    if not text:
        return default_font_size

    effective_default_font_size = default_font_size * _page_wrapped_font_scale(scene)
    figure = ax.figure
    axes_width_fraction = ax.get_position().width
    x_limits = ax.get_xlim()
    scene_width = abs(x_limits[1] - x_limits[0])
    if axes_width_fraction <= 0.0 or scene_width <= 0.0:
        return effective_default_font_size

    canvas_width_pixels = (
        figure.canvas.get_width_height()[0]
        if figure.canvas is not None
        else figure.get_size_inches()[0] * figure.dpi
    )
    available_width_fraction = 0.74
    effective_scene_width = min(
        scene_width,
        get_viewport_width(figure, default=scene_width),
    )
    axes_width_pixels = canvas_width_pixels * axes_width_fraction
    available_width_points = (
        (axes_width_pixels * (width / effective_scene_width) * available_width_fraction)
        * 72.0
        / figure.dpi
    )
    text_width_at_one_point = _text_width_in_points(text)
    if text_width_at_one_point <= 0.0:
        return effective_default_font_size

    fitted_font_size = available_width_points / text_width_at_one_point
    return max(3.5, min(effective_default_font_size, fitted_font_size))


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
