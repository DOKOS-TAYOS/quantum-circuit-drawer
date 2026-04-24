"""Axes, projection, and render-context helpers for the 3D Matplotlib renderer."""

from __future__ import annotations

import logging
from types import MethodType
from typing import TYPE_CHECKING

import numpy as np
from mpl_toolkits.mplot3d import proj3d  # type: ignore[import-untyped]

from ..exceptions import RenderingError
from ..layout.scene_3d import LayoutScene3D, Point3D
from ..managed.view_state_3d import Managed3DFixedViewState
from ..typing import OutputPath
from ._matplotlib_renderer_3d_geometry import _RenderContext3D, build_render_context_3d
from ._matplotlib_renderer_3d_viewport import axes_box_aspect_3d, viewport_short_dimension_3d
from ._render_support import save_rendered_figure

if TYPE_CHECKING:
    from matplotlib.figure import Figure, SubFigure
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from .matplotlib_renderer_3d import MatplotlibRenderer3D


def prepare_axes_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    fixed_view_state: Managed3DFixedViewState | None = None,
) -> None:
    min_x = min(point.x for point in scene.quantum_wire_positions.values())
    max_x = max(point.x for point in scene.quantum_wire_positions.values())
    max_y = max(point.y for point in scene.quantum_wire_positions.values())
    x_limits = (min_x - 1.8, max_x + 1.8)
    y_limits = (scene.classical_plane_y - 1.4, max_y + 1.8)
    z_limits = (0.0, scene.depth)
    axes.set_facecolor(scene.style.theme.axes_facecolor)
    axes.patch.set_visible(False)
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
    axes.set_axis_off()
    for axis in (axes.xaxis, axes.yaxis, axes.zaxis):
        line = getattr(axis, "line", None)
        if line is not None:
            line.set_visible(False)
        pane = getattr(axis, "pane", None)
        if pane is not None:
            pane.set_visible(False)
    if fixed_view_state is None:
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
        try:
            axes.view_init(elev=24.0, azim=-68.0, vertical_axis="y")
        except TypeError:
            axes.view_init(elev=24.0, azim=-68.0)
        return
    renderer._apply_fixed_view_state(axes, fixed_view_state)


def synchronize_axes_geometry_3d(axes: Axes3D) -> None:
    """Apply the current 3D box geometry before projecting gate sizes."""

    axes.apply_aspect()


def expand_axes_to_fill_viewport_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    viewport_bounds: tuple[float, float, float, float],
    *,
    aspect_attr: str,
) -> None:
    axes.set_position(viewport_bounds)
    renderer._install_full_viewport_aspect(axes, aspect_attr=aspect_attr)


def install_full_viewport_aspect_3d(
    axes: Axes3D,
    *,
    aspect_attr: str,
) -> None:
    if getattr(axes, aspect_attr, False):
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
    setattr(axes, aspect_attr, True)


def managed_viewport_bounds_3d(
    axes: Axes3D,
    *,
    viewport_attr: str,
) -> tuple[float, float, float, float] | None:
    bounds = getattr(axes, viewport_attr, None)
    if (
        isinstance(bounds, tuple)
        and len(bounds) == 4
        and all(isinstance(value, int | float) for value in bounds)
    ):
        left, bottom, width, height = bounds
        return (float(left), float(bottom), float(width), float(height))
    return None


def managed_fixed_view_state_3d(
    axes: Axes3D,
    *,
    fixed_state_attr: str,
) -> Managed3DFixedViewState | None:
    fixed_view_state = getattr(axes, fixed_state_attr, None)
    return fixed_view_state if isinstance(fixed_view_state, Managed3DFixedViewState) else None


def apply_fixed_view_state_3d(
    axes: Axes3D,
    fixed_view_state: Managed3DFixedViewState,
) -> None:
    axes.set_xlim(*fixed_view_state.x_limits)
    axes.set_ylim(*fixed_view_state.y_limits)
    axes.set_zlim(*fixed_view_state.z_limits)
    if fixed_view_state.raw_box_aspect is not None:
        axes._box_aspect = np.asarray(fixed_view_state.raw_box_aspect, dtype=float)

    try:
        if fixed_view_state.roll is not None:
            axes.view_init(
                elev=fixed_view_state.elev,
                azim=fixed_view_state.azim,
                roll=fixed_view_state.roll,
                vertical_axis="y",
            )
        else:
            axes.view_init(
                elev=fixed_view_state.elev,
                azim=fixed_view_state.azim,
                vertical_axis="y",
            )
    except TypeError:
        if fixed_view_state.roll is not None:
            try:
                axes.view_init(
                    elev=fixed_view_state.elev,
                    azim=fixed_view_state.azim,
                    roll=fixed_view_state.roll,
                )
            except TypeError:
                axes.view_init(elev=fixed_view_state.elev, azim=fixed_view_state.azim)
        else:
            axes.view_init(elev=fixed_view_state.elev, azim=fixed_view_state.azim)


def fit_scene_to_shorter_canvas_dimension_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    viewport_bounds: tuple[float, float, float, float] | None = None,
    render_context: _RenderContext3D | None = None,
    fill_fraction: float,
) -> None:
    context = render_context or renderer._create_render_context(axes)
    projected_scene_points = renderer._projected_scene_geometry_points(
        axes,
        scene,
        render_context=context,
    )
    if projected_scene_points.size == 0:
        return

    content_width = float(np.ptp(projected_scene_points[:, 0]))
    content_height = float(np.ptp(projected_scene_points[:, 1]))
    content_size = max(content_width, content_height)
    short_dimension = renderer._viewport_short_dimension(axes, viewport_bounds=viewport_bounds)
    if content_size <= 0.0 or short_dimension <= 0.0:
        return

    zoom = (short_dimension * fill_fraction) / content_size
    if not np.isfinite(zoom) or zoom <= 0.0:
        return
    axes.set_box_aspect(renderer._axes_box_aspect(axes), zoom=zoom)
    renderer._synchronize_axes_geometry(axes)


def axes_box_aspect_for_renderer_3d(axes: Axes3D) -> tuple[float, float, float]:
    return axes_box_aspect_3d(axes)


def viewport_short_dimension_for_renderer_3d(
    axes: Axes3D,
    *,
    viewport_bounds: tuple[float, float, float, float] | None = None,
) -> float:
    return viewport_short_dimension_3d(axes, viewport_bounds=viewport_bounds)


def projected_scene_geometry_points_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    render_context: _RenderContext3D,
) -> np.ndarray:
    point_groups = [
        renderer._topology_plane_points(scene),
        renderer._wire_geometry_points(scene),
        renderer._connection_geometry_points(scene),
        renderer._gate_geometry_points(axes, scene, render_context=render_context),
        renderer._marker_geometry_points(scene),
        renderer._text_geometry_points(scene),
    ]
    non_empty_groups = [points for points in point_groups if points.size > 0]
    if not non_empty_groups:
        return np.empty((0, 2), dtype=float)
    return renderer._projected_display_points(
        axes,
        np.vstack(non_empty_groups),
        render_context=render_context,
    )


def create_render_context_3d(
    axes: Axes3D,
    *,
    x_target_ring_segments: int,
) -> _RenderContext3D:
    return build_render_context_3d(
        axes,
        x_target_ring_segments=x_target_ring_segments,
    )


def projected_axis_scales_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    center: Point3D,
    *,
    render_context: _RenderContext3D | None = None,
) -> tuple[float, float, float]:
    context = render_context or renderer._create_render_context(axes)
    center_key = (center.x, center.y, center.z)
    cached_scales = context.projected_axis_scale_cache.get(center_key)
    if cached_scales is not None:
        return cached_scales
    projected_points = renderer._projected_display_points(
        axes,
        np.array(
            [
                (center.x, center.y, center.z),
                (center.x + 1.0, center.y, center.z),
                (center.x, center.y + 1.0, center.z),
                (center.x, center.y, center.z + 1.0),
            ],
            dtype=float,
        ),
        render_context=context,
    )
    origin = projected_points[0]
    scales = (
        float(np.linalg.norm(projected_points[1] - origin)),
        float(np.linalg.norm(projected_points[2] - origin)),
        float(np.linalg.norm(projected_points[3] - origin)),
    )
    context.projected_axis_scale_cache[center_key] = scales
    return scales


def projected_display_points_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    points: np.ndarray,
    *,
    render_context: _RenderContext3D | None = None,
) -> np.ndarray:
    del renderer
    if points.size == 0:
        return np.empty((0, 2), dtype=float)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError("points must be an Nx3 array")

    context = render_context or create_render_context_3d(axes, x_target_ring_segments=40)
    projected_x, projected_y, _ = proj3d.proj_transform(
        points[:, 0],
        points[:, 1],
        points[:, 2],
        context.projection_matrix,
    )
    projected_xy = np.column_stack(
        (
            np.asarray(projected_x, dtype=float),
            np.asarray(projected_y, dtype=float),
        )
    )
    return np.asarray(context.data_transform.transform(projected_xy), dtype=float)


def save_output_3d(
    figure: Figure | SubFigure,
    output: OutputPath | None,
    *,
    logger: logging.Logger,
) -> None:
    try:
        save_rendered_figure(figure, output)
    except RenderingError as exc:
        logger.debug("Failed to save rendered 3D circuit to %r: %s", output, exc)
        raise
