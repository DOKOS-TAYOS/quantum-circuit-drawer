"""Geometry containers and low-level array helpers for the 3D renderer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from ..layout.scene_3d import SceneGate3D

if TYPE_CHECKING:
    from matplotlib.transforms import Transform
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

Segment3D = tuple[tuple[float, float, float], tuple[float, float, float]]


@dataclass(slots=True)
class _PreparedBatchedGateGeometry3D:
    geometry_points: np.ndarray
    box_faces: list[list[tuple[float, float, float]]]
    measurement_faces: list[list[tuple[float, float, float]]]
    measurement_gates: list[SceneGate3D]
    x_target_ring_segments: list[Segment3D]
    x_target_cross_segments: list[Segment3D]


@dataclass(slots=True)
class _RenderContext3D:
    projection_matrix: np.ndarray
    data_transform: Transform
    projected_axis_scale_cache: dict[tuple[float, float, float], tuple[float, float, float]]
    x_target_unit_circle: np.ndarray
    prepared_gate_geometry: _PreparedBatchedGateGeometry3D | None = None


def point_array_3d(points: list[tuple[float, float, float]]) -> np.ndarray:
    """Convert a point list into the dense array form used by the renderer."""

    if not points:
        return np.empty((0, 3), dtype=float)
    return np.array(points, dtype=float)


def build_render_context_3d(
    axes: Axes3D,
    *,
    x_target_ring_segments: int,
) -> _RenderContext3D:
    """Build the render context cache for one 3D axes."""

    theta = np.linspace(0.0, 2.0 * np.pi, x_target_ring_segments, endpoint=False)
    unit_circle = np.column_stack((np.cos(theta), np.sin(theta)))
    return _RenderContext3D(
        projection_matrix=axes.get_proj(),
        data_transform=axes.transData,
        projected_axis_scale_cache={},
        x_target_unit_circle=unit_circle,
    )
