"""Matplotlib 3D renderer for topology-aware scenes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, cast

import numpy as np
from matplotlib.artist import Artist
from matplotlib.backend_bases import MouseEvent
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
from .base import BaseRenderer

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_QUANTUM_WIRE_COLOR = "#ffffff"
_CONTROL_CONNECTION_COLOR = "#22c55e"
_TOPOLOGY_EDGE_COLOR = "#facc15"
_QUANTUM_WIRE_WIDTH_SCALE = 0.68
_CONTROL_CONNECTION_WIDTH_SCALE = 1.55
_TOPOLOGY_EDGE_WIDTH_SCALE = 0.6
_HOVER_ZORDER = 10_000.0


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
        if axes is None:
            managed_figure, axes = create_managed_figure(scene, use_agg=True, projection="3d")
            logger.debug("Rendering 3D scene on renderer-managed Agg figure")
        assert axes is not None
        axes_3d = cast("Axes3D", axes)
        figure = axes_3d.figure
        figure.patch.set_facecolor(scene.style.theme.figure_facecolor)
        self._prepare_axes(axes_3d, scene)

        hover_targets: list[tuple[Artist, str]] = []
        hover_targets.extend(self._draw_wires(axes_3d, scene))
        hover_targets.extend(self._draw_connections(axes_3d, scene))
        hover_targets.extend(self._draw_gates(axes_3d, scene))
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
        axes.set_facecolor(scene.style.theme.axes_facecolor)
        axes.set_xlim(min_x - 1.8, max_x + 1.8)
        axes.set_ylim(scene.classical_plane_y - 1.4, max_y + 1.8)
        axes.set_zlim(0.0, scene.depth)
        axes.set_box_aspect((scene.width, scene.height, scene.depth))
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

    def _draw_gates(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
        hover_targets: list[tuple[Artist, str]] = []
        for gate in scene.gates:
            if gate.render_style is GateRenderStyle3D.X_TARGET:
                hover_targets.extend(self._draw_x_target(axes, gate, scene))
                continue
            collection = Poly3DCollection(
                self._cuboid_faces(gate),
                facecolors=scene.style.theme.measurement_facecolor
                if gate.render_style is GateRenderStyle3D.MEASUREMENT
                else scene.style.theme.gate_facecolor,
                edgecolors=scene.style.theme.measurement_color
                if gate.render_style is GateRenderStyle3D.MEASUREMENT
                else scene.style.theme.gate_edgecolor,
                linewidths=scene.style.line_width,
                alpha=0.96,
            )
            axes.add_collection3d(collection)
            if gate.hover_text:
                hover_targets.append((collection, gate.hover_text))
            if gate.render_style is GateRenderStyle3D.MEASUREMENT and not scene.hover_enabled:
                axes.text(
                    gate.center.x,
                    gate.center.y,
                    gate.center.z,
                    "M",
                    color=scene.style.theme.text_color,
                    fontsize=scene.style.font_size * 0.86,
                    ha="center",
                    va="center",
                )
        return hover_targets

    def _draw_x_target(
        self,
        axes: Axes3D,
        gate: SceneGate3D,
        scene: LayoutScene3D,
    ) -> list[tuple[Artist, str]]:
        radius = min(gate.size_x, gate.size_y) * 0.32
        theta = np.linspace(0.0, 2.0 * np.pi, 40)
        (circle_line,) = axes.plot(
            gate.center.x + (radius * np.cos(theta)),
            gate.center.y + (radius * np.sin(theta)),
            np.full_like(theta, gate.center.z),
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

    def _draw_markers(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
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

    def _save_output(self, figure: Figure | SubFigure, output: OutputPath | None) -> None:
        if output is None:
            return

        try:
            from matplotlib.figure import SubFigure as MatplotlibSubFigure

            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            save_figure: Figure
            if isinstance(figure, MatplotlibSubFigure):
                save_figure = figure.figure
            else:
                save_figure = figure
            save_figure.savefig(output_path, bbox_inches="tight")
        except (OSError, TypeError, ValueError) as exc:
            logger.debug("Failed to save rendered 3D circuit to %r: %s", output, exc)
            raise RenderingError(f"failed to save rendered circuit to {output!r}: {exc}") from exc
