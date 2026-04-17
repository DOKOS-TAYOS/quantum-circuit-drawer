"""Matplotlib 3D renderer for topology-aware scenes."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from types import MethodType
from typing import TYPE_CHECKING, cast

import numpy as np
from matplotlib.artist import Artist
from matplotlib.backend_bases import MouseEvent
from mpl_toolkits.mplot3d import proj3d  # type: ignore[import-untyped]
from mpl_toolkits.mplot3d.art3d import (  # type: ignore[import-untyped]
    Line3DCollection,
    Poly3DCollection,
)

from ..exceptions import RenderingError
from ..layout.scene import LayoutScene
from ..layout.scene_3d import (
    ConnectionRenderStyle3D,
    GateRenderStyle3D,
    LayoutScene3D,
    MarkerStyle3D,
    Point3D,
    SceneConnection3D,
    SceneGate3D,
)
from ..typing import OutputPath, RenderResult
from ._matplotlib_figure import create_managed_figure
from ._render_support import save_rendered_figure
from .base import BaseRenderer

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    from matplotlib.transforms import Transform
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_QUANTUM_WIRE_COLOR = "#ffffff"
_CONTROL_CONNECTION_COLOR = "#22c55e"
_TOPOLOGY_EDGE_COLOR = "#facc15"
_QUANTUM_WIRE_WIDTH_SCALE = 0.68
_CONTROL_CONNECTION_WIDTH_SCALE = 1.55
_TOPOLOGY_EDGE_WIDTH_SCALE = 0.6
_GATE_EDGE_WIDTH_SCALE = 0.56
_HOVER_ZORDER = 10_000.0
_CUBIC_GATE_SIZE_TOLERANCE = 1e-6
_X_TARGET_RING_SEGMENTS = 40
_SCENE_FIT_FILL_FRACTION = 0.92
_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
_MANAGED_3D_FULL_VIEWPORT_ASPECT_ATTR = "_quantum_circuit_drawer_managed_3d_full_viewport_aspect"


@dataclass(slots=True)
class _RenderContext3D:
    projection_matrix: np.ndarray
    data_transform: Transform
    projected_axis_scale_cache: dict[tuple[float, float, float], tuple[float, float, float]]
    x_target_unit_circle: np.ndarray


class MatplotlibRenderer3D(BaseRenderer):
    """Render a topology-aware scene using Matplotlib 3D primitives."""

    backend_name = "matplotlib"

    def render(
        self,
        scene: LayoutScene | LayoutScene3D,
        *,
        ax: Axes | None = None,
        output: OutputPath | None = None,
    ) -> RenderResult:
        if not isinstance(scene, LayoutScene3D):
            raise TypeError("MatplotlibRenderer3D only supports 3D layout scenes")
        axes = ax
        managed_figure = None
        viewport_bounds: tuple[float, float, float, float] | None = None
        if axes is None:
            managed_figure, axes = create_managed_figure(scene, use_agg=True, projection="3d")
            logger.debug("Rendering 3D scene on renderer-managed Agg figure")
        assert axes is not None
        axes_3d = cast("Axes3D", axes)
        viewport_bounds = self._managed_viewport_bounds(axes_3d)
        if viewport_bounds is None and managed_figure is not None:
            viewport_bounds = (0.0, 0.0, 1.0, 1.0)
        figure = axes_3d.figure
        figure.patch.set_facecolor(scene.style.theme.figure_facecolor)
        self._prepare_axes(axes_3d, scene)
        if viewport_bounds is not None:
            self._expand_axes_to_fill_viewport(axes_3d, viewport_bounds)
        self._synchronize_axes_geometry(axes_3d)
        self._fit_scene_to_shorter_canvas_dimension(
            axes_3d,
            scene,
            viewport_bounds=viewport_bounds,
        )
        render_context = self._create_render_context(axes_3d)

        hover_targets: list[tuple[Artist, str]] = []
        self._draw_topology_planes(axes_3d, scene)
        hover_targets.extend(self._draw_wires(axes_3d, scene))
        hover_targets.extend(self._draw_connections(axes_3d, scene))
        hover_targets.extend(self._draw_gates(axes_3d, scene, render_context))
        hover_targets.extend(self._draw_markers(axes_3d, scene))
        self._draw_texts(axes_3d, scene)
        if scene.hover_enabled:
            self._attach_hover(axes_3d, hover_targets)

        self._save_output(figure, output)
        if ax is None:
            assert managed_figure is not None
            return managed_figure, axes_3d
        return axes_3d

    def _prepare_axes(self, axes: Axes3D, scene: LayoutScene3D) -> None:
        min_x = min(point.x for point in scene.quantum_wire_positions.values())
        max_x = max(point.x for point in scene.quantum_wire_positions.values())
        max_y = max(point.y for point in scene.quantum_wire_positions.values())
        x_limits = (min_x - 1.8, max_x + 1.8)
        y_limits = (scene.classical_plane_y - 1.4, max_y + 1.8)
        z_limits = (0.0, scene.depth)
        axes.set_facecolor(scene.style.theme.axes_facecolor)
        axes.set_xlim(*x_limits)
        axes.set_ylim(*y_limits)
        axes.set_zlim(*z_limits)
        axes.set_box_aspect(
            (
                x_limits[1] - x_limits[0],
                y_limits[1] - y_limits[0],
                z_limits[1] - z_limits[0],
            )
        )
        axes.grid(False)
        axes.set_xticks([])
        axes.set_yticks([])
        axes.set_zticks([])
        axes.set_xlabel("")
        axes.set_ylabel("")
        axes.set_zlabel("")
        axes.xaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
        axes.yaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
        axes.zaxis.set_pane_color((0.0, 0.0, 0.0, 0.0))
        axes.set_proj_type("persp")
        try:
            axes.view_init(elev=18.0, azim=-55.0, vertical_axis="y")
        except TypeError:
            axes.view_init(elev=18.0, azim=-55.0)

    def _synchronize_axes_geometry(self, axes: Axes3D) -> None:
        """Apply the current 3D box geometry before projecting gate sizes."""

        axes.apply_aspect()

    def _expand_axes_to_fill_viewport(
        self,
        axes: Axes3D,
        viewport_bounds: tuple[float, float, float, float],
    ) -> None:
        axes.set_position(viewport_bounds)
        self._install_full_viewport_aspect(axes)

    def _install_full_viewport_aspect(self, axes: Axes3D) -> None:
        if getattr(axes, _MANAGED_3D_FULL_VIEWPORT_ASPECT_ATTR, False):
            return

        def _apply_full_viewport_aspect(
            managed_axes: Axes3D,
            position: object | None = None,
        ) -> None:
            active_position = (
                position if position is not None else managed_axes.get_position(original=True)
            )
            managed_axes._set_position(active_position, "active")

        axes.apply_aspect = MethodType(_apply_full_viewport_aspect, axes)
        setattr(axes, _MANAGED_3D_FULL_VIEWPORT_ASPECT_ATTR, True)

    def _managed_viewport_bounds(
        self,
        axes: Axes3D,
    ) -> tuple[float, float, float, float] | None:
        bounds = getattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, None)
        if (
            isinstance(bounds, tuple)
            and len(bounds) == 4
            and all(isinstance(value, int | float) for value in bounds)
        ):
            left, bottom, width, height = bounds
            return (float(left), float(bottom), float(width), float(height))
        return None

    def _fit_scene_to_shorter_canvas_dimension(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        viewport_bounds: tuple[float, float, float, float] | None = None,
    ) -> None:
        render_context = self._create_render_context(axes)
        projected_scene_points = self._projected_scene_geometry_points(
            axes,
            scene,
            render_context=render_context,
        )
        if projected_scene_points.size == 0:
            return

        content_width = float(np.ptp(projected_scene_points[:, 0]))
        content_height = float(np.ptp(projected_scene_points[:, 1]))
        content_size = max(content_width, content_height)
        short_dimension = self._viewport_short_dimension(axes, viewport_bounds=viewport_bounds)
        if content_size <= 0.0 or short_dimension <= 0.0:
            return

        zoom = (short_dimension * _SCENE_FIT_FILL_FRACTION) / content_size
        if not np.isfinite(zoom) or zoom <= 0.0:
            return
        axes.set_box_aspect(self._axes_box_aspect(axes), zoom=zoom)
        self._synchronize_axes_geometry(axes)

    def _axes_box_aspect(self, axes: Axes3D) -> tuple[float, float, float]:
        x_limits = axes.get_xlim3d()
        y_limits = axes.get_ylim3d()
        z_limits = axes.get_zlim3d()
        return (
            float(x_limits[1] - x_limits[0]),
            float(y_limits[1] - y_limits[0]),
            float(z_limits[1] - z_limits[0]),
        )

    def _viewport_short_dimension(
        self,
        axes: Axes3D,
        *,
        viewport_bounds: tuple[float, float, float, float] | None = None,
    ) -> float:
        if viewport_bounds is None:
            return min(float(axes.bbox.width), float(axes.bbox.height))
        _, _, width, height = viewport_bounds
        canvas_width, canvas_height = axes.figure.canvas.get_width_height()
        return min(width * float(canvas_width), height * float(canvas_height))

    def _projected_scene_geometry_points(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        render_context: _RenderContext3D,
    ) -> np.ndarray:
        scene_points: list[Point3D] = []
        scene_points.extend(self._topology_plane_points(scene))
        scene_points.extend(self._wire_geometry_points(scene))
        scene_points.extend(self._connection_geometry_points(scene))
        scene_points.extend(self._gate_geometry_points(axes, scene, render_context=render_context))
        scene_points.extend(self._marker_geometry_points(scene))
        scene_points.extend(text.position for text in scene.texts)
        if not scene_points:
            return np.empty((0, 2), dtype=float)
        return np.array(
            [
                self._projected_display_point(
                    axes,
                    point,
                    render_context=render_context,
                )
                for point in scene_points
            ],
            dtype=float,
        )

    def _topology_plane_points(self, scene: LayoutScene3D) -> list[Point3D]:
        return [
            Point3D(x=x_value, y=y_value, z=plane.z)
            for plane in scene.topology_planes
            for x_value, y_value in (
                (plane.x_min, plane.y_min),
                (plane.x_max, plane.y_min),
                (plane.x_max, plane.y_max),
                (plane.x_min, plane.y_max),
            )
        ]

    def _wire_geometry_points(self, scene: LayoutScene3D) -> list[Point3D]:
        points: list[Point3D] = []
        for wire in scene.wires:
            if wire.double_line:
                for delta in (-0.06, 0.06):
                    points.extend(
                        (
                            Point3D(x=wire.start.x + delta, y=wire.start.y, z=wire.start.z),
                            Point3D(x=wire.end.x + delta, y=wire.end.y, z=wire.end.z),
                        )
                    )
                continue
            points.extend((wire.start, wire.end))
        return points

    def _connection_geometry_points(self, scene: LayoutScene3D) -> list[Point3D]:
        points: list[Point3D] = []
        for connection in scene.connections:
            points.extend(connection.points)
            if connection.arrow_at_end:
                for start, end in self._arrowhead_segments(connection.points):
                    points.extend((Point3D(*start), Point3D(*end)))
        return points

    def _gate_geometry_points(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        render_context: _RenderContext3D,
    ) -> list[Point3D]:
        points: list[Point3D] = []
        for gate in scene.gates:
            if gate.render_style is GateRenderStyle3D.X_TARGET:
                radius = min(gate.size_x, gate.size_y) * 0.32
                ring_points = self._x_target_ring_points(gate, radius, render_context)
                points.extend(Point3D(float(x), float(y), float(z)) for x, y, z in ring_points)
                points.extend(
                    (
                        Point3D(gate.center.x - radius, gate.center.y, gate.center.z),
                        Point3D(gate.center.x + radius, gate.center.y, gate.center.z),
                        Point3D(gate.center.x, gate.center.y - radius, gate.center.z),
                        Point3D(gate.center.x, gate.center.y + radius, gate.center.z),
                    )
                )
                continue
            display_gate = self._display_compensated_gate(
                axes,
                gate,
                render_context=render_context,
            )
            points.extend(
                Point3D(*vertex) for face in self._cuboid_faces(display_gate) for vertex in face
            )
        return points

    def _marker_geometry_points(self, scene: LayoutScene3D) -> list[Point3D]:
        points: list[Point3D] = []
        for marker in scene.markers:
            if marker.style is MarkerStyle3D.SWAP:
                size = marker.size
                points.extend(
                    (
                        Point3D(marker.center.x - size, marker.center.y - size, marker.center.z),
                        Point3D(marker.center.x + size, marker.center.y + size, marker.center.z),
                        Point3D(marker.center.x - size, marker.center.y + size, marker.center.z),
                        Point3D(marker.center.x + size, marker.center.y - size, marker.center.z),
                    )
                )
                continue
            points.append(marker.center)
        return points

    def _create_render_context(self, axes: Axes3D) -> _RenderContext3D:
        theta = np.linspace(0.0, 2.0 * np.pi, _X_TARGET_RING_SEGMENTS, endpoint=False)
        unit_circle = np.column_stack((np.cos(theta), np.sin(theta)))
        return _RenderContext3D(
            projection_matrix=axes.get_proj(),
            data_transform=axes.transData,
            projected_axis_scale_cache={},
            x_target_unit_circle=unit_circle,
        )

    def _draw_wires(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
        hover_targets: list[tuple[Artist, str]] = []
        for wire in scene.wires:
            if wire.double_line:
                offset = 0.06
                line = None
                for delta in (-offset, offset):
                    (line,) = axes.plot(
                        [wire.start.x + delta, wire.end.x + delta],
                        [wire.start.y, wire.end.y],
                        [wire.start.z, wire.end.z],
                        color=scene.style.theme.classical_wire_color,
                        linewidth=scene.style.line_width,
                        zorder=1.0,
                    )
                if line is not None and wire.hover_text:
                    hover_targets.append((line, wire.hover_text))
                continue
            (line,) = axes.plot(
                [wire.start.x, wire.end.x],
                [wire.start.y, wire.end.y],
                [wire.start.z, wire.end.z],
                color=_QUANTUM_WIRE_COLOR,
                linewidth=scene.style.line_width * _QUANTUM_WIRE_WIDTH_SCALE,
                zorder=1.1,
            )
            if wire.hover_text:
                hover_targets.append((line, wire.hover_text))
        return hover_targets

    def _draw_connections(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
    ) -> list[tuple[Artist, str]]:
        hover_targets: list[tuple[Artist, str]] = []
        for connection in scene.connections:
            segments = self._segments_for_points(connection.points)
            if not segments:
                logger.debug(
                    "Skipping degenerate 3D connection in column=%d with %d point(s)",
                    connection.column,
                    len(connection.points),
                )
                continue
            if connection.arrow_at_end:
                segments.extend(self._arrowhead_segments(connection.points))
            connection_color = self._connection_color(connection, scene)
            connection_width = self._connection_line_width(connection, scene)
            if connection.is_classical and connection.double_line:
                draw_segments: list[
                    tuple[tuple[float, float, float], tuple[float, float, float]]
                ] = []
                for delta in (-0.05, 0.05):
                    draw_segments.extend(
                        (
                            (first[0] + delta, first[1], first[2]),
                            (second[0] + delta, second[1], second[2]),
                        )
                        for first, second in segments
                    )
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
            if connection.label:
                label_point = connection.points[-1]
                axes.text(
                    label_point.x + 0.08,
                    label_point.y,
                    label_point.z,
                    connection.label,
                    color=scene.style.theme.classical_wire_color
                    if connection.is_classical
                    else scene.style.theme.wire_color,
                    fontsize=scene.style.font_size * 0.72,
                )
            if connection.hover_text:
                hover_targets.append((collection, connection.hover_text))
        return hover_targets

    def _draw_gates(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> list[tuple[Artist, str]]:
        hover_targets: list[tuple[Artist, str]] = []
        batched_x_targets: list[SceneGate3D] = []
        for gate in scene.gates:
            if gate.render_style is GateRenderStyle3D.X_TARGET:
                if scene.hover_enabled:
                    hover_targets.extend(self._draw_x_target(axes, gate, scene, render_context))
                else:
                    batched_x_targets.append(gate)
                continue
            display_gate = self._display_compensated_gate(axes, gate, render_context=render_context)
            collection = Poly3DCollection(
                self._cuboid_faces(display_gate),
                facecolors=scene.style.theme.measurement_facecolor
                if gate.render_style is GateRenderStyle3D.MEASUREMENT
                else scene.style.theme.gate_facecolor,
                edgecolors=scene.style.theme.measurement_color
                if gate.render_style is GateRenderStyle3D.MEASUREMENT
                else scene.style.theme.gate_edgecolor,
                linewidths=scene.style.line_width * _GATE_EDGE_WIDTH_SCALE,
                alpha=0.96,
            )
            axes.add_collection3d(collection)
            if gate.hover_text:
                hover_targets.append((collection, gate.hover_text))
            if gate.render_style is GateRenderStyle3D.MEASUREMENT and not scene.hover_enabled:
                self._draw_measurement_symbol(axes, display_gate, scene)
        if batched_x_targets:
            self._draw_x_targets_batched(axes, batched_x_targets, scene, render_context)
        return hover_targets

    def _draw_topology_planes(self, axes: Axes3D, scene: LayoutScene3D) -> None:
        for plane in scene.topology_planes:
            collection = Poly3DCollection(
                [
                    [
                        (plane.x_min, plane.y_min, plane.z),
                        (plane.x_max, plane.y_min, plane.z),
                        (plane.x_max, plane.y_max, plane.z),
                        (plane.x_min, plane.y_max, plane.z),
                    ]
                ],
                facecolors=plane.color,
                edgecolors="none",
                alpha=plane.alpha,
            )
            collection.set_zorder(0.2)
            axes.add_collection3d(collection)

    def _draw_x_target(
        self,
        axes: Axes3D,
        gate: SceneGate3D,
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> list[tuple[Artist, str]]:
        radius = min(gate.size_x, gate.size_y) * 0.32
        ring_points = self._x_target_ring_points(gate, radius, render_context)
        closed_ring_points = np.vstack((ring_points, ring_points[0]))
        (circle_line,) = axes.plot(
            closed_ring_points[:, 0],
            closed_ring_points[:, 1],
            closed_ring_points[:, 2],
            color=scene.style.theme.wire_color,
            linewidth=scene.style.line_width,
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
            colors=scene.style.theme.wire_color,
            linewidths=scene.style.line_width,
        )
        axes.add_collection3d(cross_collection)
        return [(circle_line, gate.hover_text)] if gate.hover_text else []

    def _draw_x_targets_batched(
        self,
        axes: Axes3D,
        gates: list[SceneGate3D],
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> None:
        ring_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        cross_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        for gate in gates:
            radius = min(gate.size_x, gate.size_y) * 0.32
            ring_segments.extend(
                self._segments_for_ring_points(
                    self._x_target_ring_points(gate, radius, render_context)
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
        ring_collection = Line3DCollection(
            ring_segments,
            colors=scene.style.theme.wire_color,
            linewidths=scene.style.line_width,
        )
        ring_collection.set_zorder(3.3)
        axes.add_collection3d(ring_collection)
        cross_collection = Line3DCollection(
            cross_segments,
            colors=scene.style.theme.wire_color,
            linewidths=scene.style.line_width,
        )
        cross_collection.set_zorder(3.4)
        axes.add_collection3d(cross_collection)

    def _draw_markers(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
        if scene.hover_enabled:
            return self._draw_markers_with_hover(axes, scene)
        return self._draw_markers_batched(axes, scene)

    def _draw_markers_with_hover(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
    ) -> list[tuple[Artist, str]]:
        hover_targets: list[tuple[Artist, str]] = []
        for marker in scene.markers:
            if marker.style is MarkerStyle3D.TOPOLOGY_NODE:
                axes.scatter(
                    [marker.center.x],
                    [marker.center.y],
                    [marker.center.z],
                    s=marker.size * 320.0,
                    facecolors=scene.style.theme.axes_facecolor,
                    edgecolors=_QUANTUM_WIRE_COLOR,
                    linewidths=max(1.0, scene.style.line_width * 0.82),
                    depthshade=False,
                    zorder=3.2,
                )
                continue
            if marker.style is MarkerStyle3D.CONTROL:
                artist = axes.scatter(
                    [marker.center.x],
                    [marker.center.y],
                    [marker.center.z],
                    s=marker.size * 18.0,
                    c=_CONTROL_CONNECTION_COLOR,
                    depthshade=False,
                    zorder=3.4,
                )
                hover_targets.append((artist, "control"))
                continue
            size = marker.size
            collection = Line3DCollection(
                [
                    (
                        (marker.center.x - size, marker.center.y - size, marker.center.z),
                        (marker.center.x + size, marker.center.y + size, marker.center.z),
                    ),
                    (
                        (marker.center.x - size, marker.center.y + size, marker.center.z),
                        (marker.center.x + size, marker.center.y - size, marker.center.z),
                    ),
                ],
                colors=scene.style.theme.wire_color,
                linewidths=scene.style.line_width,
            )
            collection.set_zorder(3.1)
            axes.add_collection3d(collection)
        return hover_targets

    def _draw_markers_batched(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
        topology_nodes = [
            marker for marker in scene.markers if marker.style is MarkerStyle3D.TOPOLOGY_NODE
        ]
        if topology_nodes:
            axes.scatter(
                [marker.center.x for marker in topology_nodes],
                [marker.center.y for marker in topology_nodes],
                [marker.center.z for marker in topology_nodes],
                s=[marker.size * 320.0 for marker in topology_nodes],
                facecolors=scene.style.theme.axes_facecolor,
                edgecolors=_QUANTUM_WIRE_COLOR,
                linewidths=max(1.0, scene.style.line_width * 0.82),
                depthshade=False,
                zorder=3.2,
            )

        control_markers = [
            marker for marker in scene.markers if marker.style is MarkerStyle3D.CONTROL
        ]
        if control_markers:
            axes.scatter(
                [marker.center.x for marker in control_markers],
                [marker.center.y for marker in control_markers],
                [marker.center.z for marker in control_markers],
                s=[marker.size * 18.0 for marker in control_markers],
                c=_CONTROL_CONNECTION_COLOR,
                depthshade=False,
                zorder=3.4,
            )

        swap_segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        for marker in scene.markers:
            if marker.style is not MarkerStyle3D.SWAP:
                continue
            size = marker.size
            swap_segments.extend(
                [
                    (
                        (marker.center.x - size, marker.center.y - size, marker.center.z),
                        (marker.center.x + size, marker.center.y + size, marker.center.z),
                    ),
                    (
                        (marker.center.x - size, marker.center.y + size, marker.center.z),
                        (marker.center.x + size, marker.center.y - size, marker.center.z),
                    ),
                ]
            )
        if swap_segments:
            collection = Line3DCollection(
                swap_segments,
                colors=scene.style.theme.wire_color,
                linewidths=scene.style.line_width,
            )
            collection.set_zorder(3.1)
            axes.add_collection3d(collection)
        return []

    def _draw_measurement_symbol(
        self,
        axes: Axes3D,
        gate: SceneGate3D,
        scene: LayoutScene3D,
    ) -> None:
        top_z = gate.center.z + (gate.size_z * 0.53)
        theta = np.linspace(np.pi, 2.0 * np.pi, 32)
        arc_x = gate.center.x + (gate.size_x * 0.26 * np.cos(theta))
        arc_y = gate.center.y - (gate.size_y * 0.06) + (gate.size_y * 0.24 * np.sin(theta))
        axes.plot(
            arc_x,
            arc_y,
            np.full_like(theta, top_z),
            color=scene.style.theme.measurement_color,
            linewidth=scene.style.line_width,
            solid_capstyle="round",
            zorder=3.6,
        )
        axes.plot(
            [
                gate.center.x - (gate.size_x * 0.04),
                gate.center.x + (gate.size_x * 0.16),
            ],
            [
                gate.center.y - (gate.size_y * 0.12),
                gate.center.y + (gate.size_y * 0.16),
            ],
            [top_z, top_z],
            color=scene.style.theme.measurement_color,
            linewidth=scene.style.line_width,
            solid_capstyle="round",
            zorder=3.6,
        )

    def _draw_texts(self, axes: Axes3D, scene: LayoutScene3D) -> None:
        for text in scene.texts:
            axes.text(
                text.position.x,
                text.position.y,
                text.position.z,
                text.text,
                ha=text.ha,
                va=text.va,
                fontsize=text.font_size or scene.style.font_size,
                color=scene.style.theme.text_color,
            )

    def _attach_hover(self, axes: Axes3D, hover_targets: list[tuple[Artist, str]]) -> None:
        figure = axes.figure
        annotation = axes.annotate(
            "",
            xy=(0.0, 0.0),
            xytext=(10.0, 10.0),
            xycoords="figure pixels",
            textcoords="offset points",
            visible=False,
            bbox={"boxstyle": "round,pad=0.18", "fc": "#222222", "ec": "#cccccc", "alpha": 0.9},
            color="#ffffff",
            annotation_clip=False,
        )
        annotation.set_zorder(_HOVER_ZORDER)
        annotation.set_clip_on(False)

        def _on_move(event: MouseEvent) -> None:
            if getattr(event, "inaxes", None) is not axes:
                if annotation.get_visible():
                    annotation.set_visible(False)
                    figure.canvas.draw_idle()
                return
            for artist, text in hover_targets:
                contains, _ = artist.contains(event) if hasattr(artist, "contains") else (False, {})
                if contains:
                    annotation.xy = (
                        float(getattr(event, "x", 0.0)),
                        float(getattr(event, "y", 0.0)),
                    )
                    annotation.set_text(text)
                    annotation.set_visible(True)
                    figure.canvas.draw_idle()
                    return
            if annotation.get_visible():
                annotation.set_visible(False)
                figure.canvas.draw_idle()

        if figure.canvas is not None:
            figure.canvas.mpl_connect("motion_notify_event", _on_move)

    def _connection_color(
        self,
        connection: SceneConnection3D,
        scene: LayoutScene3D,
    ) -> str:
        if connection.is_classical:
            return scene.style.theme.classical_wire_color
        if connection.render_style is ConnectionRenderStyle3D.CONTROL:
            return _CONTROL_CONNECTION_COLOR
        if connection.render_style is ConnectionRenderStyle3D.TOPOLOGY_EDGE:
            return _TOPOLOGY_EDGE_COLOR
        return scene.style.theme.wire_color

    def _connection_line_width(
        self,
        connection: SceneConnection3D,
        scene: LayoutScene3D,
    ) -> float:
        if connection.is_classical:
            return scene.style.line_width
        if connection.render_style is ConnectionRenderStyle3D.CONTROL:
            return scene.style.line_width * _CONTROL_CONNECTION_WIDTH_SCALE
        if connection.render_style is ConnectionRenderStyle3D.TOPOLOGY_EDGE:
            return scene.style.line_width * _TOPOLOGY_EDGE_WIDTH_SCALE
        return scene.style.line_width

    def _segments_for_points(
        self,
        points: tuple[Point3D, ...],
    ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
        return [
            (
                (first.x, first.y, first.z),
                (second.x, second.y, second.z),
            )
            for first, second in zip(points, points[1:])
        ]

    def _segments_for_ring_points(
        self,
        points: np.ndarray,
    ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
        point_count = points.shape[0]
        return [
            (
                (float(points[index][0]), float(points[index][1]), float(points[index][2])),
                (
                    float(points[(index + 1) % point_count][0]),
                    float(points[(index + 1) % point_count][1]),
                    float(points[(index + 1) % point_count][2]),
                ),
            )
            for index in range(point_count)
        ]

    def _x_target_ring_points(
        self,
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

    def _arrowhead_segments(
        self,
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

    def _cuboid_faces(self, gate: SceneGate3D) -> list[list[tuple[float, float, float]]]:
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

    def _display_compensated_gate(
        self,
        axes: Axes3D,
        gate: SceneGate3D,
        render_context: _RenderContext3D | None = None,
    ) -> SceneGate3D:
        if not self._should_compensate_gate(gate):
            return gate

        scale_x, scale_y, scale_z = self._projected_axis_scales(
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

    def _should_compensate_gate(self, gate: SceneGate3D) -> bool:
        if gate.render_style is GateRenderStyle3D.X_TARGET:
            return False
        return (
            abs(gate.size_x - gate.size_y) <= _CUBIC_GATE_SIZE_TOLERANCE
            and abs(gate.size_y - gate.size_z) <= _CUBIC_GATE_SIZE_TOLERANCE
        )

    def _projected_axis_scales(
        self,
        axes: Axes3D,
        center: Point3D,
        *,
        render_context: _RenderContext3D | None = None,
    ) -> tuple[float, float, float]:
        context = render_context or self._create_render_context(axes)
        center_key = (center.x, center.y, center.z)
        cached_scales = context.projected_axis_scale_cache.get(center_key)
        if cached_scales is not None:
            return cached_scales
        origin = self._projected_display_point(axes, center, render_context=context)
        x_axis_point = self._projected_display_point(
            axes,
            Point3D(x=center.x + 1.0, y=center.y, z=center.z),
            render_context=context,
        )
        y_axis_point = self._projected_display_point(
            axes,
            Point3D(x=center.x, y=center.y + 1.0, z=center.z),
            render_context=context,
        )
        z_axis_point = self._projected_display_point(
            axes,
            Point3D(x=center.x, y=center.y, z=center.z + 1.0),
            render_context=context,
        )
        scales = (
            float(np.linalg.norm(x_axis_point - origin)),
            float(np.linalg.norm(y_axis_point - origin)),
            float(np.linalg.norm(z_axis_point - origin)),
        )
        context.projected_axis_scale_cache[center_key] = scales
        return scales

    def _projected_display_point(
        self,
        axes: Axes3D,
        point: Point3D,
        *,
        render_context: _RenderContext3D | None = None,
    ) -> np.ndarray:
        context = render_context or self._create_render_context(axes)
        projected_x, projected_y, _ = proj3d.proj_transform(
            point.x,
            point.y,
            point.z,
            context.projection_matrix,
        )
        display_x, display_y = context.data_transform.transform((projected_x, projected_y))
        return np.array([float(display_x), float(display_y)], dtype=float)

    def _save_output(self, figure: Figure | SubFigure, output: OutputPath | None) -> None:
        try:
            save_rendered_figure(figure, output)
        except RenderingError as exc:
            logger.debug("Failed to save rendered 3D circuit to %r: %s", output, exc)
            raise
