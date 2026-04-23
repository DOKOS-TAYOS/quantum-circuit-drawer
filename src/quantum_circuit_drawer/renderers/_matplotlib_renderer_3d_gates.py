"""Gate helpers for the 3D Matplotlib renderer."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import numpy as np
from matplotlib.artist import Artist
from mpl_toolkits.mplot3d.art3d import (  # type: ignore[import-untyped]
    Line3DCollection,
    Poly3DCollection,
)

from ..layout.scene_3d import GateRenderStyle3D, LayoutScene3D, SceneGate3D
from ..style import resolved_gate_edge_line_width, resolved_wire_line_width
from ._matplotlib_figure import append_artist_click_target
from ._matplotlib_renderer_3d_geometry import _PreparedBatchedGateGeometry3D, _RenderContext3D
from ._matplotlib_visual_state import (
    alpha_for_visual_state,
    color_for_visual_state,
    gate_facecolor_for_visual_state,
    line_width_scale_for_visual_state,
    measurement_facecolor_for_visual_state,
)
from ._render_support import backend_supports_interaction, figure_backend_name

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ._matplotlib_renderer_3d_geometry import Segment3D
    from .matplotlib_renderer_3d import MatplotlibRenderer3D


_CUBIC_GATE_SIZE_TOLERANCE = 1e-6


def gate_geometry_points_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    render_context: _RenderContext3D,
) -> np.ndarray:
    if renderer._should_prepare_batched_gate_geometry_offscreen(axes, scene):
        return renderer._prepare_batched_gate_geometry_offscreen(
            axes,
            scene,
            render_context=render_context,
        ).geometry_points

    point_groups: list[np.ndarray] = []
    for gate in scene.gates:
        if gate.render_style is GateRenderStyle3D.X_TARGET:
            radius = min(gate.size_x, gate.size_y) * 0.32
            ring_points = renderer._x_target_ring_points(gate, radius, render_context)
            point_groups.append(ring_points)
            point_groups.append(
                np.array(
                    [
                        (gate.center.x - radius, gate.center.y, gate.center.z),
                        (gate.center.x + radius, gate.center.y, gate.center.z),
                        (gate.center.x, gate.center.y - radius, gate.center.z),
                        (gate.center.x, gate.center.y + radius, gate.center.z),
                    ],
                    dtype=float,
                )
            )
            continue
        display_gate = renderer._display_compensated_gate(
            axes,
            gate,
            render_context=render_context,
        )
        point_groups.append(
            np.array(
                [vertex for face in renderer._cuboid_faces(display_gate) for vertex in face],
                dtype=float,
            )
        )
    if not point_groups:
        return np.empty((0, 3), dtype=float)
    return np.vstack(point_groups)


def should_prepare_batched_gate_geometry_offscreen_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
) -> bool:
    if scene.hover_enabled:
        return False
    if renderer._managed_viewport_bounds(axes) is None:
        return False
    return not backend_supports_interaction(figure_backend_name(axes.figure))


def prepare_batched_gate_geometry_offscreen_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    render_context: _RenderContext3D,
) -> _PreparedBatchedGateGeometry3D:
    prepared_geometry = render_context.prepared_gate_geometry
    if prepared_geometry is not None:
        return prepared_geometry

    point_groups: list[np.ndarray] = []
    box_faces: list[list[tuple[float, float, float]]] = []
    measurement_faces: list[list[tuple[float, float, float]]] = []
    measurement_gates: list[SceneGate3D] = []
    x_target_ring_segments: list[Segment3D] = []
    x_target_cross_segments: list[Segment3D] = []

    for gate in scene.gates:
        if gate.render_style is GateRenderStyle3D.X_TARGET:
            radius = min(gate.size_x, gate.size_y) * 0.32
            ring_points = renderer._x_target_ring_points(gate, radius, render_context)
            x_target_ring_segments.extend(renderer._segments_for_ring_points(ring_points))
            x_target_cross_segments.extend(
                [
                    (
                        (gate.center.x - radius, gate.center.y, gate.center.z),
                        (gate.center.x + radius, gate.center.y, gate.center.z),
                    ),
                    (
                        (gate.center.x, gate.center.y - radius, gate.center.z),
                        (gate.center.x, gate.center.y + radius, gate.center.z),
                    ),
                ]
            )
            point_groups.append(ring_points)
            point_groups.append(
                np.array(
                    [
                        (gate.center.x - radius, gate.center.y, gate.center.z),
                        (gate.center.x + radius, gate.center.y, gate.center.z),
                        (gate.center.x, gate.center.y - radius, gate.center.z),
                        (gate.center.x, gate.center.y + radius, gate.center.z),
                    ],
                    dtype=float,
                )
            )
            continue

        display_gate = renderer._display_compensated_gate(
            axes,
            gate,
            render_context=render_context,
        )
        gate_faces = renderer._cuboid_faces(display_gate)
        point_groups.append(
            np.array([vertex for face in gate_faces for vertex in face], dtype=float)
        )
        if gate.render_style is GateRenderStyle3D.MEASUREMENT:
            measurement_faces.extend(gate_faces)
            measurement_gates.append(display_gate)
            continue
        box_faces.extend(gate_faces)

    geometry_points = np.vstack(point_groups) if point_groups else np.empty((0, 3), dtype=float)
    prepared_geometry = _PreparedBatchedGateGeometry3D(
        geometry_points=geometry_points,
        box_faces=box_faces,
        measurement_faces=measurement_faces,
        measurement_gates=measurement_gates,
        x_target_ring_segments=x_target_ring_segments,
        x_target_cross_segments=x_target_cross_segments,
    )
    render_context.prepared_gate_geometry = prepared_geometry
    return prepared_geometry


def draw_gates_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    render_context: _RenderContext3D,
) -> list[tuple[Artist, str]]:
    if scene.hover_enabled or _requires_individual_gate_artists(scene):
        return draw_gates_with_hover_3d(renderer, axes, scene, render_context)
    draw_gates_batched_3d(renderer, axes, scene, render_context)
    return []


def draw_gates_with_hover_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    render_context: _RenderContext3D,
) -> list[tuple[Artist, str]]:
    hover_targets: list[tuple[Artist, str]] = []
    for gate in scene.gates:
        if gate.group_highlighted:
            _draw_group_highlight_overlay_3d(
                renderer,
                axes,
                gate,
                render_context,
                scene,
            )
        if gate.render_style is GateRenderStyle3D.X_TARGET:
            hover_targets.extend(renderer._draw_x_target(axes, gate, scene, render_context))
            continue
        display_gate = renderer._display_compensated_gate(axes, gate, render_context=render_context)
        collection = Poly3DCollection(
            renderer._cuboid_faces(display_gate),
            facecolors=_gate_facecolor_3d(scene, gate),
            edgecolors=color_for_visual_state(
                scene.style.theme.measurement_color
                if gate.render_style is GateRenderStyle3D.MEASUREMENT
                else scene.style.theme.gate_edgecolor,
                theme=scene.style.theme,
                visual_state=gate.visual_state,
            ),
            linewidths=resolved_gate_edge_line_width(scene.style)
            * line_width_scale_for_visual_state(gate.visual_state),
            alpha=0.96 * alpha_for_visual_state(gate.visual_state),
        )
        axes.add_collection3d(collection)
        if gate.operation_id is not None:
            append_artist_click_target(
                axes,
                artist=collection,
                operation_id=gate.operation_id,
                priority=40,
            )
        if gate.hover_text:
            hover_targets.append((collection, gate.hover_text))
    return hover_targets


def _gate_facecolor_3d(scene: LayoutScene3D, gate: SceneGate3D) -> str:
    if gate.render_style is GateRenderStyle3D.MEASUREMENT:
        return measurement_facecolor_for_visual_state(
            theme=scene.style.theme,
            visual_state=gate.visual_state,
        )
    return gate_facecolor_for_visual_state(
        theme=scene.style.theme,
        visual_state=gate.visual_state,
    )


def _draw_group_highlight_overlay_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    gate: SceneGate3D,
    render_context: _RenderContext3D,
    scene: LayoutScene3D,
) -> None:
    padded_gate = replace(
        gate,
        size_x=gate.size_x * 1.14,
        size_y=gate.size_y * 1.14,
        size_z=gate.size_z * 1.18,
    )
    display_gate = renderer._display_compensated_gate(
        axes,
        padded_gate,
        render_context=render_context,
    )
    overlay = Poly3DCollection(
        renderer._cuboid_faces(display_gate),
        facecolors=scene.style.theme.accent_color,
        edgecolors="none",
        alpha=0.11,
    )
    overlay.set_zorder(2.1)
    axes.add_collection3d(overlay)


def _requires_individual_gate_artists(scene: LayoutScene3D) -> bool:
    return any(
        gate.operation_id is not None
        or gate.visual_state.name != "DEFAULT"
        or gate.group_highlighted
        for gate in scene.gates
    )


def draw_gates_batched_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    render_context: _RenderContext3D,
) -> None:
    batched_x_targets: list[SceneGate3D] = []
    box_faces: list[list[tuple[float, float, float]]] = []
    measurement_faces: list[list[tuple[float, float, float]]] = []
    measurement_gates: list[SceneGate3D] = []
    prepared_geometry: _PreparedBatchedGateGeometry3D | None = None

    if renderer._should_prepare_batched_gate_geometry_offscreen(axes, scene):
        prepared_geometry = renderer._prepare_batched_gate_geometry_offscreen(
            axes,
            scene,
            render_context=render_context,
        )
        box_faces = prepared_geometry.box_faces
        measurement_faces = prepared_geometry.measurement_faces
        measurement_gates = prepared_geometry.measurement_gates
    else:
        for gate in scene.gates:
            if gate.render_style is GateRenderStyle3D.X_TARGET:
                batched_x_targets.append(gate)
                continue
            display_gate = renderer._display_compensated_gate(
                axes,
                gate,
                render_context=render_context,
            )
            if gate.render_style is GateRenderStyle3D.MEASUREMENT:
                measurement_faces.extend(renderer._cuboid_faces(display_gate))
                measurement_gates.append(display_gate)
                continue
            box_faces.extend(renderer._cuboid_faces(display_gate))

    if box_faces:
        collection = Poly3DCollection(
            box_faces,
            facecolors=scene.style.theme.gate_facecolor,
            edgecolors=scene.style.theme.gate_edgecolor,
            linewidths=resolved_gate_edge_line_width(scene.style),
            alpha=0.96,
        )
        axes.add_collection3d(collection)
    if measurement_faces:
        collection = Poly3DCollection(
            measurement_faces,
            facecolors=scene.style.theme.measurement_facecolor,
            edgecolors=scene.style.theme.measurement_color,
            linewidths=resolved_gate_edge_line_width(scene.style),
            alpha=0.96,
        )
        axes.add_collection3d(collection)
        renderer._draw_measurement_symbols_batched(axes, measurement_gates, scene)
    if prepared_geometry is not None:
        renderer._draw_x_target_segment_collections(
            axes,
            prepared_geometry.x_target_ring_segments,
            prepared_geometry.x_target_cross_segments,
            scene,
        )
    elif batched_x_targets:
        renderer._draw_x_targets_batched(axes, batched_x_targets, scene, render_context)


def draw_x_target_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    gate: SceneGate3D,
    scene: LayoutScene3D,
    render_context: _RenderContext3D,
) -> list[tuple[Artist, str]]:
    radius = min(gate.size_x, gate.size_y) * 0.32
    ring_points = renderer._x_target_ring_points(gate, radius, render_context)
    closed_ring_points = np.vstack((ring_points, ring_points[0]))
    (circle_line,) = axes.plot(
        closed_ring_points[:, 0],
        closed_ring_points[:, 1],
        closed_ring_points[:, 2],
        color=color_for_visual_state(
            scene.style.theme.wire_color,
            theme=scene.style.theme,
            visual_state=gate.visual_state,
        ),
        linewidth=resolved_wire_line_width(scene.style)
        * line_width_scale_for_visual_state(gate.visual_state),
        alpha=alpha_for_visual_state(gate.visual_state),
    )
    cross_collection = Line3DCollection(
        [
            (
                (gate.center.x - radius, gate.center.y, gate.center.z),
                (gate.center.x + radius, gate.center.y, gate.center.z),
            ),
            (
                (gate.center.x, gate.center.y - radius, gate.center.z),
                (gate.center.x, gate.center.y + radius, gate.center.z),
            ),
        ],
        colors=color_for_visual_state(
            scene.style.theme.wire_color,
            theme=scene.style.theme,
            visual_state=gate.visual_state,
        ),
        linewidths=resolved_wire_line_width(scene.style)
        * line_width_scale_for_visual_state(gate.visual_state),
        alpha=alpha_for_visual_state(gate.visual_state),
    )
    axes.add_collection3d(cross_collection)
    if gate.operation_id is not None:
        append_artist_click_target(
            axes,
            artist=circle_line,
            operation_id=gate.operation_id,
            priority=40,
        )
        append_artist_click_target(
            axes,
            artist=cross_collection,
            operation_id=gate.operation_id,
            priority=45,
        )
    hover_targets: list[tuple[Artist, str]] = []
    if gate.hover_text:
        hover_targets.append((circle_line, gate.hover_text))
        hover_targets.append((cross_collection, gate.hover_text))
    return hover_targets


def draw_x_targets_batched_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    gates: list[SceneGate3D],
    scene: LayoutScene3D,
    render_context: _RenderContext3D,
) -> None:
    ring_segments: list[Segment3D] = []
    cross_segments: list[Segment3D] = []
    for gate in gates:
        radius = min(gate.size_x, gate.size_y) * 0.32
        ring_segments.extend(
            renderer._segments_for_ring_points(
                renderer._x_target_ring_points(gate, radius, render_context)
            )
        )
        cross_segments.extend(
            [
                (
                    (gate.center.x - radius, gate.center.y, gate.center.z),
                    (gate.center.x + radius, gate.center.y, gate.center.z),
                ),
                (
                    (gate.center.x, gate.center.y - radius, gate.center.z),
                    (gate.center.x, gate.center.y + radius, gate.center.z),
                ),
            ]
        )
    renderer._draw_x_target_segment_collections(
        axes,
        ring_segments,
        cross_segments,
        scene,
    )


def draw_x_target_segment_collections_3d(
    axes: Axes3D,
    ring_segments: list[Segment3D],
    cross_segments: list[Segment3D],
    scene: LayoutScene3D,
) -> None:
    if not ring_segments and not cross_segments:
        return
    ring_collection = Line3DCollection(
        ring_segments,
        colors=scene.style.theme.wire_color,
        linewidths=resolved_wire_line_width(scene.style),
    )
    ring_collection.set_zorder(3.3)
    axes.add_collection3d(ring_collection)
    cross_collection = Line3DCollection(
        cross_segments,
        colors=scene.style.theme.wire_color,
        linewidths=resolved_wire_line_width(scene.style),
    )
    cross_collection.set_zorder(3.4)
    axes.add_collection3d(cross_collection)


def x_target_ring_points_3d(
    gate: SceneGate3D,
    radius: float,
    render_context: _RenderContext3D,
) -> np.ndarray:
    ring_points = render_context.x_target_unit_circle * radius
    z_values = np.full((ring_points.shape[0], 1), gate.center.z)
    return np.column_stack(
        (
            gate.center.x + ring_points[:, 0],
            gate.center.y + ring_points[:, 1],
            z_values[:, 0],
        )
    )


def cuboid_faces_3d(gate: SceneGate3D) -> list[list[tuple[float, float, float]]]:
    half_x = gate.size_x / 2
    half_y = gate.size_y / 2
    half_z = gate.size_z / 2
    x0, x1 = gate.center.x - half_x, gate.center.x + half_x
    y0, y1 = gate.center.y - half_y, gate.center.y + half_y
    z0, z1 = gate.center.z - half_z, gate.center.z + half_z
    return [
        [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
        [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
        [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
    ]


def display_compensated_gate_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    gate: SceneGate3D,
    render_context: _RenderContext3D | None = None,
) -> SceneGate3D:
    if not renderer._should_compensate_gate(gate):
        return gate

    scale_x, scale_y, scale_z = renderer._projected_axis_scales(
        axes,
        gate.center,
        render_context=render_context,
    )
    if min(scale_x, scale_y, scale_z) <= 0.0:
        return gate

    target_display_size = min(
        gate.size_x * scale_x,
        gate.size_y * scale_y,
        gate.size_z * scale_z,
    )
    if target_display_size <= 0.0:
        return gate

    return replace(
        gate,
        size_x=target_display_size / scale_x,
        size_y=target_display_size / scale_y,
        size_z=target_display_size / scale_z,
    )


def should_compensate_gate_3d(gate: SceneGate3D) -> bool:
    if gate.render_style is GateRenderStyle3D.X_TARGET:
        return False
    return (
        abs(gate.size_x - gate.size_y) <= _CUBIC_GATE_SIZE_TOLERANCE
        and abs(gate.size_y - gate.size_z) <= _CUBIC_GATE_SIZE_TOLERANCE
    )
