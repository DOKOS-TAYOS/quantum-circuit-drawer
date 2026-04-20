"""Viewport and camera-fitting helpers for the Matplotlib 3D renderer."""

from __future__ import annotations

from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]


def axes_box_aspect_3d(axes: Axes3D) -> tuple[float, float, float]:
    """Return the extents-based box aspect of the current 3D axes."""

    x_limits = axes.get_xlim3d()
    y_limits = axes.get_ylim3d()
    z_limits = axes.get_zlim3d()
    return (
        float(x_limits[1] - x_limits[0]),
        float(y_limits[1] - y_limits[0]),
        float(z_limits[1] - z_limits[0]),
    )


def viewport_short_dimension_3d(
    axes: Axes3D,
    *,
    viewport_bounds: tuple[float, float, float, float] | None = None,
) -> float:
    """Return the shorter visible canvas dimension for one 3D viewport."""

    if viewport_bounds is None:
        return min(float(axes.bbox.width), float(axes.bbox.height))
    _, _, width, height = viewport_bounds
    canvas_width, canvas_height = axes.figure.canvas.get_width_height()
    return min(width * float(canvas_width), height * float(canvas_height))
