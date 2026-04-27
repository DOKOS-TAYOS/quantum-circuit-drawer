"""Wire and connection helpers for the 3D Matplotlib renderer."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # type: ignore[import-untyped]

from ..layout.scene_3d import ConnectionRenderStyle3D, LayoutScene3D, Point3D, SceneConnection3D
from ..style import (
    resolved_classical_wire_line_width,
    resolved_connection_line_width,
    resolved_topology_edge_line_width,
    resolved_wire_line_width,
)
from ..utils.formatting import format_visible_label
from ._matplotlib_figure import append_artist_click_target
from ._matplotlib_visual_state import (
    alpha_for_visual_state,
    color_for_visual_state,
    line_width_scale_for_visual_state,
)

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from .matplotlib_renderer_3d import MatplotlibRenderer3D

from ._matplotlib_renderer_3d_geometry import Segment3D
from ._matplotlib_renderer_3d_hover import HoverTarget3D


def wire_geometry_points_3d(scene: LayoutScene3D) -> np.ndarray:
    points: list[tuple[float, float, float]] = []
    for wire in scene.wires:
        if wire.double_line:
            for delta in (-0.06, 0.06):
                points.extend(
                    (
                        (wire.start.x + delta, wire.start.y, wire.start.z),
                        (wire.end.x + delta, wire.end.y, wire.end.z),
                    )
                )
            continue
        points.extend(
            (
                (wire.start.x, wire.start.y, wire.start.z),
                (wire.end.x, wire.end.y, wire.end.z),
            )
        )
    return np.asarray(points, dtype=float) if points else np.empty((0, 3), dtype=float)


def connection_geometry_points_3d(
    renderer: MatplotlibRenderer3D,
    scene: LayoutScene3D,
) -> np.ndarray:
    points: list[tuple[float, float, float]] = []
    for connection in scene.connections:
        points.extend((point.x, point.y, point.z) for point in connection.points)
        if connection.arrow_at_end:
            for start, end in renderer._arrowhead_segments(connection.points):
                points.extend((start, end))
    return np.asarray(points, dtype=float) if points else np.empty((0, 3), dtype=float)


def draw_wires_3d(axes: Axes3D, scene: LayoutScene3D) -> list[HoverTarget3D]:
    hover_targets: list[HoverTarget3D] = []
    for wire in scene.wires:
        wire_color = color_for_visual_state(
            scene.style.theme.classical_wire_color
            if wire.double_line
            else scene.style.theme.wire_color,
            theme=scene.style.theme,
            visual_state=wire.visual_state,
        )
        wire_alpha = alpha_for_visual_state(wire.visual_state)
        if wire.double_line:
            offset = 0.06
            line = None
            for delta in (-offset, offset):
                (line,) = axes.plot(
                    [wire.start.x + delta, wire.end.x + delta],
                    [wire.start.y, wire.end.y],
                    [wire.start.z, wire.end.z],
                    color=wire_color,
                    linewidth=resolved_classical_wire_line_width(scene.style)
                    * line_width_scale_for_visual_state(wire.visual_state),
                    alpha=wire_alpha,
                    zorder=1.0,
                )
            if line is not None and wire.hover_text:
                hover_targets.append((line, wire.hover_text))
            continue
        (line,) = axes.plot(
            [wire.start.x, wire.end.x],
            [wire.start.y, wire.end.y],
            [wire.start.z, wire.end.z],
            color=wire_color,
            linewidth=resolved_wire_line_width(scene.style)
            * line_width_scale_for_visual_state(wire.visual_state),
            alpha=wire_alpha,
            zorder=1.1,
        )
        if wire.hover_text:
            hover_targets.append((line, wire.hover_text))
    return hover_targets


def draw_connections_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
) -> list[HoverTarget3D]:
    if scene.hover_enabled or _requires_individual_connection_artists(scene):
        return draw_connections_with_hover_3d(renderer, axes, scene)
    draw_connections_batched_3d(renderer, axes, scene)
    return []


def draw_connections_with_hover_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
) -> list[HoverTarget3D]:
    hover_targets: list[HoverTarget3D] = []
    for connection in scene.connections:
        segments = renderer._connection_segments(connection)
        if not segments:
            continue
        connection_color = renderer._connection_color(connection, scene)
        connection_width = renderer._connection_line_width(connection, scene)
        if connection.is_classical and connection.double_line:
            draw_segments: list[Segment3D] = []
            for delta in (-0.05, 0.05):
                draw_segments.extend(renderer._offset_segments_along_x(segments, delta=delta))
            collection = Line3DCollection(
                draw_segments,
                colors=connection_color,
                linewidths=connection_width,
            )
        else:
            collection = Line3DCollection(
                segments,
                colors=connection_color,
                linewidths=connection_width,
                linestyles="dashed" if connection.is_classical else "solid",
            )
        collection.set_zorder(
            2.4 if connection.render_style is ConnectionRenderStyle3D.CONTROL else 0.8
        )
        axes.add_collection3d(collection)
        if connection.operation_id is not None:
            append_artist_click_target(
                axes,
                artist=collection,
                operation_id=connection.operation_id,
                priority=25,
            )
        if connection.label:
            renderer._draw_connection_label(axes, connection, scene)
        if connection.hover_data is not None:
            hover_targets.append((collection, connection.hover_data))
        elif connection.hover_text:
            hover_targets.append((collection, connection.hover_text))
    return hover_targets


def draw_connections_batched_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
) -> None:
    standard_segments: list[Segment3D] = []
    control_segments: list[Segment3D] = []
    topology_segments: list[Segment3D] = []
    classical_segments: list[Segment3D] = []
    classical_double_segments: list[Segment3D] = []

    for connection in scene.connections:
        segments = renderer._connection_segments(connection)
        if not segments:
            continue
        if connection.is_classical and connection.double_line:
            for delta in (-0.05, 0.05):
                classical_double_segments.extend(
                    renderer._offset_segments_along_x(segments, delta=delta)
                )
        elif connection.is_classical:
            classical_segments.extend(segments)
        elif connection.render_style is ConnectionRenderStyle3D.CONTROL:
            control_segments.extend(segments)
        elif connection.render_style is ConnectionRenderStyle3D.TOPOLOGY_EDGE:
            topology_segments.extend(segments)
        else:
            standard_segments.extend(segments)

        if connection.label:
            renderer._draw_connection_label(axes, connection, scene)

    if standard_segments:
        collection = Line3DCollection(
            standard_segments,
            colors=scene.style.theme.wire_color,
            linewidths=resolved_connection_line_width(scene.style),
            linestyles="solid",
        )
        collection.set_zorder(0.8)
        axes.add_collection3d(collection)
    if control_segments:
        collection = Line3DCollection(
            control_segments,
            colors=scene.style.theme.control_connection_color or scene.style.theme.accent_color,
            linewidths=resolved_connection_line_width(scene.style),
            linestyles="solid",
        )
        collection.set_zorder(2.4)
        axes.add_collection3d(collection)
    if topology_segments:
        collection = Line3DCollection(
            topology_segments,
            colors=scene.style.theme.topology_edge_color or scene.style.theme.accent_color,
            linewidths=resolved_topology_edge_line_width(scene.style),
            linestyles="solid",
        )
        collection.set_zorder(0.8)
        axes.add_collection3d(collection)
    if classical_segments:
        collection = Line3DCollection(
            classical_segments,
            colors=scene.style.theme.classical_wire_color,
            linewidths=resolved_classical_wire_line_width(scene.style),
            linestyles="dashed",
        )
        collection.set_zorder(0.8)
        axes.add_collection3d(collection)
    if classical_double_segments:
        collection = Line3DCollection(
            classical_double_segments,
            colors=scene.style.theme.classical_wire_color,
            linewidths=resolved_classical_wire_line_width(scene.style),
        )
        collection.set_zorder(0.8)
        axes.add_collection3d(collection)


def connection_color_3d(
    connection: SceneConnection3D,
    scene: LayoutScene3D,
) -> str:
    if connection.is_classical:
        base_color = scene.style.theme.classical_wire_color
    elif connection.render_style is ConnectionRenderStyle3D.CONTROL:
        base_color = scene.style.theme.control_connection_color or scene.style.theme.accent_color
    elif connection.render_style is ConnectionRenderStyle3D.TOPOLOGY_EDGE:
        base_color = scene.style.theme.topology_edge_color or scene.style.theme.accent_color
    else:
        base_color = scene.style.theme.wire_color
    return color_for_visual_state(
        base_color,
        theme=scene.style.theme,
        visual_state=connection.visual_state,
    )


def connection_line_width_3d(
    connection: SceneConnection3D,
    scene: LayoutScene3D,
) -> float:
    if connection.is_classical:
        return resolved_classical_wire_line_width(scene.style) * line_width_scale_for_visual_state(
            connection.visual_state
        )
    if connection.render_style is ConnectionRenderStyle3D.CONTROL:
        return resolved_connection_line_width(scene.style) * line_width_scale_for_visual_state(
            connection.visual_state
        )
    if connection.render_style is ConnectionRenderStyle3D.TOPOLOGY_EDGE:
        return resolved_topology_edge_line_width(scene.style) * line_width_scale_for_visual_state(
            connection.visual_state
        )
    return resolved_connection_line_width(scene.style) * line_width_scale_for_visual_state(
        connection.visual_state
    )


def draw_connection_label_3d(
    axes: Axes3D,
    connection: SceneConnection3D,
    scene: LayoutScene3D,
) -> None:
    label_point = connection.points[-1]
    visible_label = format_visible_label(
        connection.label or "",
        use_mathtext=scene.style.use_mathtext,
    )
    axes.text(
        label_point.x + 0.08,
        label_point.y,
        label_point.z,
        visible_label,
        color=connection_color_3d(connection, scene),
        fontsize=scene.style.font_size * 0.72,
        alpha=alpha_for_visual_state(connection.visual_state),
    )


def connection_segments_3d(
    renderer: MatplotlibRenderer3D,
    connection: SceneConnection3D,
    *,
    logger: logging.Logger,
) -> list[Segment3D]:
    segments = renderer._segments_for_points(connection.points)
    if not segments:
        logger.debug(
            "Skipping degenerate 3D connection in column=%d with %d point(s)",
            connection.column,
            len(connection.points),
        )
        return []
    if connection.arrow_at_end:
        segments.extend(renderer._arrowhead_segments(connection.points))
    return segments


def offset_segments_along_x_3d(
    segments: list[Segment3D],
    *,
    delta: float,
) -> list[Segment3D]:
    return [
        (
            (first[0] + delta, first[1], first[2]),
            (second[0] + delta, second[1], second[2]),
        )
        for first, second in segments
    ]


def _requires_individual_connection_artists(scene: LayoutScene3D) -> bool:
    return any(
        connection.operation_id is not None or connection.visual_state.name != "DEFAULT"
        for connection in scene.connections
    )


def arrowhead_segments_3d(
    points: tuple[Point3D, ...],
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    if len(points) < 2:
        return []

    start = points[-2]
    end = points[-1]
    direction = np.array(
        [end.x - start.x, end.y - start.y, end.z - start.z],
        dtype=float,
    )
    norm = float(np.linalg.norm(direction))
    if norm <= 0.0:
        return []

    unit = direction / norm
    head_length = 0.22
    half_width = 0.1
    base = np.array([end.x, end.y, end.z], dtype=float) - (unit * head_length)
    perpendicular = np.array([-unit[1], unit[0], 0.0], dtype=float)
    perpendicular_norm = float(np.linalg.norm(perpendicular))
    if perpendicular_norm <= 0.0:
        perpendicular = np.array([0.0, 1.0, 0.0], dtype=float)
    else:
        perpendicular = perpendicular / perpendicular_norm

    left = base + (perpendicular * half_width)
    right = base - (perpendicular * half_width)
    left_point = (float(left[0]), float(left[1]), float(left[2]))
    right_point = (float(right[0]), float(right[1]), float(right[2]))
    tip = (end.x, end.y, end.z)
    return [
        (left_point, tip),
        (right_point, tip),
    ]
