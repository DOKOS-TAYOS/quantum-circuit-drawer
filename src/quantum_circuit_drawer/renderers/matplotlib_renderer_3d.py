"""Matplotlib 3D renderer for topology-aware scenes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import numpy as np
from matplotlib.artist import Artist

from ..layout.scene import LayoutScene
from ..layout.scene_3d import (
    LayoutScene3D,
    Point3D,
    SceneConnection3D,
    SceneGate3D,
)
from ..managed.view_state_3d import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    Managed3DFixedViewState,
)
from ..typing import OutputPath, RenderResult
from ._matplotlib_figure import clear_hover_state, create_managed_figure
from ._matplotlib_renderer_3d_axes import (
    apply_fixed_view_state_3d,
    axes_box_aspect_for_renderer_3d,
    create_render_context_3d,
    expand_axes_to_fill_viewport_3d,
    fit_scene_to_shorter_canvas_dimension_3d,
    install_full_viewport_aspect_3d,
    managed_fixed_view_state_3d,
    managed_viewport_bounds_3d,
    prepare_axes_3d,
    projected_axis_scales_3d,
    projected_display_points_3d,
    projected_scene_geometry_points_3d,
    save_output_3d,
    synchronize_axes_geometry_3d,
    viewport_short_dimension_for_renderer_3d,
)
from ._matplotlib_renderer_3d_gates import (
    cuboid_faces_3d,
    display_compensated_gate_3d,
    draw_gates_3d,
    draw_gates_batched_3d,
    draw_gates_with_hover_3d,
    draw_x_target_3d,
    draw_x_target_segment_collections_3d,
    draw_x_targets_batched_3d,
    gate_geometry_points_3d,
    prepare_batched_gate_geometry_offscreen_3d,
    should_compensate_gate_3d,
    should_prepare_batched_gate_geometry_offscreen_3d,
    x_target_ring_points_3d,
)
from ._matplotlib_renderer_3d_geometry import (
    Segment3D,
    _PreparedBatchedGateGeometry3D,
    _RenderContext3D,
    point_array_3d,
)
from ._matplotlib_renderer_3d_markers import (
    attach_hover_targets_3d,
    clear_batched_text_artists_3d,
    draw_markers_3d,
    draw_markers_batched_3d,
    draw_markers_with_hover_3d,
    draw_measurement_symbols_batched_3d,
    draw_texts_3d,
    draw_texts_batched_offscreen_3d,
    draw_texts_standard_3d,
    marker_geometry_points_3d,
    should_batch_offscreen_texts_3d,
    text_geometry_points_3d,
)
from ._matplotlib_renderer_3d_segments import (
    segments_for_path_points_3d,
    segments_for_points_3d,
    segments_for_ring_points_3d,
)
from ._matplotlib_renderer_3d_topology import draw_topology_planes_3d, topology_plane_points_3d
from ._matplotlib_renderer_3d_wires import (
    arrowhead_segments_3d,
    connection_color_3d,
    connection_geometry_points_3d,
    connection_line_width_3d,
    connection_segments_3d,
    draw_connection_label_3d,
    draw_connections_3d,
    draw_connections_batched_3d,
    draw_connections_with_hover_3d,
    draw_wires_3d,
    offset_segments_along_x_3d,
    wire_geometry_points_3d,
)
from .base import BaseRenderer

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_X_TARGET_RING_SEGMENTS = 40
_SCENE_FIT_FILL_FRACTION = 0.92
_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
_MANAGED_3D_FULL_VIEWPORT_ASPECT_ATTR = "_quantum_circuit_drawer_managed_3d_full_viewport_aspect"
_BATCHED_3D_TEXT_ARTISTS_ATTR = "_quantum_circuit_drawer_batched_3d_text_artists"
_BATCHED_3D_TEXT_ARTIST_GID = "quantum-circuit-drawer-3d-batched-text"
_TEXT_LAYER_ZORDER = 6.0


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
            setattr(axes_3d, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, viewport_bounds)
        figure = axes_3d.figure
        fixed_view_state = self._managed_fixed_view_state(axes_3d)
        self._clear_batched_text_artists(axes_3d)
        clear_hover_state(axes_3d)
        figure.patch.set_facecolor(scene.style.theme.figure_facecolor)
        self._prepare_axes(axes_3d, scene, fixed_view_state=fixed_view_state)
        if viewport_bounds is not None:
            self._expand_axes_to_fill_viewport(axes_3d, viewport_bounds)
        self._synchronize_axes_geometry(axes_3d)
        if fixed_view_state is None:
            fit_render_context = self._create_render_context(axes_3d)
            self._fit_scene_to_shorter_canvas_dimension(
                axes_3d,
                scene,
                viewport_bounds=viewport_bounds,
                render_context=fit_render_context,
            )
            render_context = self._create_render_context(axes_3d)
            render_context.prepared_gate_geometry = fit_render_context.prepared_gate_geometry
        else:
            render_context = self._create_render_context(axes_3d)

        self._draw_topology_planes(axes_3d, scene)
        wire_hover_targets = self._draw_wires(axes_3d, scene)
        connection_hover_targets = self._draw_connections(axes_3d, scene)
        gate_hover_targets = self._draw_gates(axes_3d, scene, render_context)
        marker_hover_targets = self._draw_markers(axes_3d, scene)
        hover_targets = [
            *gate_hover_targets,
            *marker_hover_targets,
            *connection_hover_targets,
            *wire_hover_targets,
        ]
        self._draw_texts(
            axes_3d,
            scene,
            render_context=render_context,
            managed_render=managed_figure is not None,
        )
        if scene.hover_enabled:
            self._attach_hover(axes_3d, scene, hover_targets)

        self._save_output(figure, output)
        if ax is None:
            assert managed_figure is not None
            return managed_figure, axes_3d
        return axes_3d

    def _prepare_axes(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        fixed_view_state: Managed3DFixedViewState | None = None,
    ) -> None:
        prepare_axes_3d(self, axes, scene, fixed_view_state=fixed_view_state)

    def _synchronize_axes_geometry(self, axes: Axes3D) -> None:
        synchronize_axes_geometry_3d(axes)

    def _expand_axes_to_fill_viewport(
        self,
        axes: Axes3D,
        viewport_bounds: tuple[float, float, float, float],
    ) -> None:
        expand_axes_to_fill_viewport_3d(
            self,
            axes,
            viewport_bounds,
            aspect_attr=_MANAGED_3D_FULL_VIEWPORT_ASPECT_ATTR,
        )

    def _install_full_viewport_aspect(
        self,
        axes: Axes3D,
        *,
        aspect_attr: str = _MANAGED_3D_FULL_VIEWPORT_ASPECT_ATTR,
    ) -> None:
        install_full_viewport_aspect_3d(axes, aspect_attr=aspect_attr)

    def _managed_viewport_bounds(
        self,
        axes: Axes3D,
    ) -> tuple[float, float, float, float] | None:
        return managed_viewport_bounds_3d(
            axes,
            viewport_attr=_MANAGED_3D_VIEWPORT_BOUNDS_ATTR,
        )

    def _managed_fixed_view_state(self, axes: Axes3D) -> Managed3DFixedViewState | None:
        return managed_fixed_view_state_3d(
            axes,
            fixed_state_attr=_MANAGED_3D_FIXED_VIEW_STATE_ATTR,
        )

    def _apply_fixed_view_state(
        self,
        axes: Axes3D,
        fixed_view_state: Managed3DFixedViewState,
    ) -> None:
        apply_fixed_view_state_3d(axes, fixed_view_state)

    def _fit_scene_to_shorter_canvas_dimension(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        viewport_bounds: tuple[float, float, float, float] | None = None,
        render_context: _RenderContext3D | None = None,
    ) -> None:
        fit_scene_to_shorter_canvas_dimension_3d(
            self,
            axes,
            scene,
            viewport_bounds=viewport_bounds,
            render_context=render_context,
            fill_fraction=_SCENE_FIT_FILL_FRACTION,
        )

    def _axes_box_aspect(self, axes: Axes3D) -> tuple[float, float, float]:
        return axes_box_aspect_for_renderer_3d(axes)

    def _viewport_short_dimension(
        self,
        axes: Axes3D,
        *,
        viewport_bounds: tuple[float, float, float, float] | None = None,
    ) -> float:
        return viewport_short_dimension_for_renderer_3d(axes, viewport_bounds=viewport_bounds)

    def _projected_scene_geometry_points(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        render_context: _RenderContext3D,
    ) -> np.ndarray:
        return projected_scene_geometry_points_3d(
            self,
            axes,
            scene,
            render_context=render_context,
        )

    def _topology_plane_points(self, scene: LayoutScene3D) -> np.ndarray:
        return topology_plane_points_3d(scene)

    def _wire_geometry_points(self, scene: LayoutScene3D) -> np.ndarray:
        return wire_geometry_points_3d(scene)

    def _connection_geometry_points(self, scene: LayoutScene3D) -> np.ndarray:
        return connection_geometry_points_3d(self, scene)

    def _gate_geometry_points(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        render_context: _RenderContext3D,
    ) -> np.ndarray:
        return gate_geometry_points_3d(
            self,
            axes,
            scene,
            render_context=render_context,
        )

    def _should_prepare_batched_gate_geometry_offscreen(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
    ) -> bool:
        return should_prepare_batched_gate_geometry_offscreen_3d(self, axes, scene)

    def _prepare_batched_gate_geometry_offscreen(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        render_context: _RenderContext3D,
    ) -> _PreparedBatchedGateGeometry3D:
        return prepare_batched_gate_geometry_offscreen_3d(
            self,
            axes,
            scene,
            render_context=render_context,
        )

    def _marker_geometry_points(self, scene: LayoutScene3D) -> np.ndarray:
        return marker_geometry_points_3d(scene)

    def _text_geometry_points(self, scene: LayoutScene3D) -> np.ndarray:
        return text_geometry_points_3d(scene)

    def _point_array(self, points: list[tuple[float, float, float]]) -> np.ndarray:
        return point_array_3d(points)

    def _create_render_context(self, axes: Axes3D) -> _RenderContext3D:
        return create_render_context_3d(
            axes,
            x_target_ring_segments=_X_TARGET_RING_SEGMENTS,
        )

    def _draw_wires(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
        return draw_wires_3d(axes, scene)

    def _draw_connections(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
    ) -> list[tuple[Artist, str]]:
        return draw_connections_3d(self, axes, scene)

    def _draw_connections_with_hover(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
    ) -> list[tuple[Artist, str]]:
        return draw_connections_with_hover_3d(self, axes, scene)

    def _draw_connections_batched(self, axes: Axes3D, scene: LayoutScene3D) -> None:
        draw_connections_batched_3d(self, axes, scene)

    def _draw_gates(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> list[tuple[Artist, str]]:
        return draw_gates_3d(self, axes, scene, render_context)

    def _draw_gates_with_hover(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> list[tuple[Artist, str]]:
        return draw_gates_with_hover_3d(self, axes, scene, render_context)

    def _draw_gates_batched(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> None:
        draw_gates_batched_3d(self, axes, scene, render_context)

    def _draw_topology_planes(self, axes: Axes3D, scene: LayoutScene3D) -> None:
        draw_topology_planes_3d(axes, scene)

    def _draw_x_target(
        self,
        axes: Axes3D,
        gate: SceneGate3D,
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> list[tuple[Artist, str]]:
        return draw_x_target_3d(self, axes, gate, scene, render_context)

    def _draw_x_targets_batched(
        self,
        axes: Axes3D,
        gates: list[SceneGate3D],
        scene: LayoutScene3D,
        render_context: _RenderContext3D,
    ) -> None:
        draw_x_targets_batched_3d(self, axes, gates, scene, render_context)

    def _draw_x_target_segment_collections(
        self,
        axes: Axes3D,
        ring_segments: list[Segment3D],
        cross_segments: list[Segment3D],
        scene: LayoutScene3D,
    ) -> None:
        draw_x_target_segment_collections_3d(axes, ring_segments, cross_segments, scene)

    def _draw_markers(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
        return draw_markers_3d(self, axes, scene)

    def _draw_markers_with_hover(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
    ) -> list[tuple[Artist, str]]:
        return draw_markers_with_hover_3d(self, axes, scene)

    def _draw_markers_batched(self, axes: Axes3D, scene: LayoutScene3D) -> list[tuple[Artist, str]]:
        return draw_markers_batched_3d(axes, scene)

    def _draw_measurement_symbols_batched(
        self,
        axes: Axes3D,
        gates: list[SceneGate3D],
        scene: LayoutScene3D,
    ) -> None:
        draw_measurement_symbols_batched_3d(self, axes, gates, scene)

    def _draw_texts(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        render_context: _RenderContext3D,
        managed_render: bool,
    ) -> None:
        draw_texts_3d(
            self,
            axes,
            scene,
            render_context=render_context,
            managed_render=managed_render,
            batched_artists_attr=_BATCHED_3D_TEXT_ARTISTS_ATTR,
            batched_artist_gid=_BATCHED_3D_TEXT_ARTIST_GID,
            text_layer_zorder=_TEXT_LAYER_ZORDER,
        )

    def _draw_texts_standard(self, axes: Axes3D, scene: LayoutScene3D) -> None:
        draw_texts_standard_3d(axes, scene)

    def _draw_texts_batched_offscreen(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        render_context: _RenderContext3D,
    ) -> None:
        draw_texts_batched_offscreen_3d(
            self,
            axes,
            scene,
            render_context=render_context,
            batched_artists_attr=_BATCHED_3D_TEXT_ARTISTS_ATTR,
            batched_artist_gid=_BATCHED_3D_TEXT_ARTIST_GID,
            text_layer_zorder=_TEXT_LAYER_ZORDER,
        )

    def _should_batch_offscreen_texts(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        *,
        managed_render: bool,
    ) -> bool:
        return should_batch_offscreen_texts_3d(
            self,
            axes,
            scene,
            managed_render=managed_render,
        )

    def _clear_batched_text_artists(self, axes: Axes3D) -> None:
        clear_batched_text_artists_3d(
            axes,
            batched_artists_attr=_BATCHED_3D_TEXT_ARTISTS_ATTR,
        )

    def _attach_hover(
        self,
        axes: Axes3D,
        scene: LayoutScene3D,
        hover_targets: list[tuple[Artist, str]],
    ) -> None:
        attach_hover_targets_3d(axes, scene, hover_targets)

    def _connection_color(
        self,
        connection: SceneConnection3D,
        scene: LayoutScene3D,
    ) -> str:
        return connection_color_3d(connection, scene)

    def _connection_line_width(
        self,
        connection: SceneConnection3D,
        scene: LayoutScene3D,
    ) -> float:
        return connection_line_width_3d(connection, scene)

    def _draw_connection_label(
        self,
        axes: Axes3D,
        connection: SceneConnection3D,
        scene: LayoutScene3D,
    ) -> None:
        draw_connection_label_3d(axes, connection, scene)

    def _connection_segments(self, connection: SceneConnection3D) -> list[Segment3D]:
        return connection_segments_3d(self, connection, logger=logger)

    def _offset_segments_along_x(
        self,
        segments: list[Segment3D],
        *,
        delta: float,
    ) -> list[Segment3D]:
        return offset_segments_along_x_3d(segments, delta=delta)

    def _segments_for_points(
        self,
        points: tuple[Point3D, ...],
    ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
        return segments_for_points_3d(points)

    def _segments_for_ring_points(
        self,
        points: np.ndarray,
    ) -> list[Segment3D]:
        return segments_for_ring_points_3d(points)

    def _segments_for_path_points(self, points: np.ndarray) -> list[Segment3D]:
        return segments_for_path_points_3d(points)

    def _x_target_ring_points(
        self,
        gate: SceneGate3D,
        radius: float,
        render_context: _RenderContext3D,
    ) -> np.ndarray:
        return x_target_ring_points_3d(gate, radius, render_context)

    def _arrowhead_segments(
        self,
        points: tuple[Point3D, ...],
    ) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
        return arrowhead_segments_3d(points)

    def _cuboid_faces(self, gate: SceneGate3D) -> list[list[tuple[float, float, float]]]:
        return cuboid_faces_3d(gate)

    def _display_compensated_gate(
        self,
        axes: Axes3D,
        gate: SceneGate3D,
        render_context: _RenderContext3D | None = None,
    ) -> SceneGate3D:
        return display_compensated_gate_3d(self, axes, gate, render_context=render_context)

    def _should_compensate_gate(self, gate: SceneGate3D) -> bool:
        return should_compensate_gate_3d(gate)

    def _projected_axis_scales(
        self,
        axes: Axes3D,
        center: Point3D,
        *,
        render_context: _RenderContext3D | None = None,
    ) -> tuple[float, float, float]:
        return projected_axis_scales_3d(
            self,
            axes,
            center,
            render_context=render_context,
        )

    def _projected_display_points(
        self,
        axes: Axes3D,
        points: np.ndarray,
        *,
        render_context: _RenderContext3D | None = None,
    ) -> np.ndarray:
        return projected_display_points_3d(
            self,
            axes,
            points,
            render_context=render_context,
        )

    def _save_output(self, figure: Figure | SubFigure, output: OutputPath | None) -> None:
        save_output_3d(figure, output, logger=logger)
