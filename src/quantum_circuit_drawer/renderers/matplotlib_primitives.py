"""Reusable Matplotlib drawing primitives."""

from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.patches import Arc, Circle, FancyArrowPatch, FancyBboxPatch

from ..layout.scene import (
    GateRenderStyle,
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneMeasurement,
    SceneSwap,
    SceneText,
    SceneWire,
)

BASE_LAYER_ZORDER = 1
CONNECTION_LAYER_ZORDER = 2
OCCLUSION_LAYER_ZORDER = 4
SYMBOL_LAYER_ZORDER = 5
TEXT_LAYER_ZORDER = 6


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
        ax.add_patch(arrow)
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
    ax.add_patch(patch)


def draw_x_target(ax: Axes, gate: SceneGate, scene: LayoutScene) -> None:
    radius = min(gate.width, gate.height) * 0.36
    ax.add_patch(
        Circle(
            (gate.x, gate.y),
            radius=radius,
            facecolor=scene.style.theme.axes_facecolor,
            edgecolor=scene.style.theme.wire_color,
            linewidth=scene.style.line_width,
            zorder=OCCLUSION_LAYER_ZORDER,
        )
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

    ax.text(
        gate.x,
        gate.y - 0.08 if gate.subtitle else gate.y,
        gate.label,
        ha="center",
        va="center",
        fontsize=scene.style.font_size,
        color=scene.style.theme.text_color,
        zorder=TEXT_LAYER_ZORDER,
    )
    if gate.subtitle:
        ax.text(
            gate.x,
            gate.y + 0.16,
            gate.subtitle,
            ha="center",
            va="center",
            fontsize=scene.style.font_size * 0.78,
            color=scene.style.theme.text_color,
            zorder=TEXT_LAYER_ZORDER,
        )


def draw_control(ax: Axes, control: SceneControl, scene: LayoutScene) -> None:
    ax.add_patch(
        Circle(
            (control.x, control.y),
            radius=scene.style.control_radius,
            facecolor=scene.style.theme.wire_color,
            edgecolor=scene.style.theme.wire_color,
            linewidth=scene.style.line_width,
            zorder=SYMBOL_LAYER_ZORDER,
        )
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
        facecolor=scene.style.theme.gate_facecolor,
        edgecolor=scene.style.theme.measurement_color,
        linewidth=scene.style.line_width,
        zorder=OCCLUSION_LAYER_ZORDER,
    )
    ax.add_patch(patch)


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
    ax.add_patch(arc)
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


def finalize_axes(ax: Axes, scene: LayoutScene) -> None:
    ax.set_xlim(0.0, scene.width)
    ax.set_ylim(scene.height, 0.0)
    ax.set_facecolor(scene.style.theme.axes_facecolor)
    ax.axis("off")
