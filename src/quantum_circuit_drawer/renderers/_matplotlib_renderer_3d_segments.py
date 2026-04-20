"""Segment and path helpers for the Matplotlib 3D renderer."""

from __future__ import annotations

from itertools import pairwise

import numpy as np

from ..layout.scene_3d import Point3D
from ._matplotlib_renderer_3d_geometry import Segment3D


def segments_for_points_3d(points: tuple[Point3D, ...]) -> list[Segment3D]:
    """Convert point objects into line segments."""

    return [
        (
            (first.x, first.y, first.z),
            (second.x, second.y, second.z),
        )
        for first, second in pairwise(points)
    ]


def segments_for_ring_points_3d(points: np.ndarray) -> list[Segment3D]:
    """Build closed-ring segments from ring point coordinates."""

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


def segments_for_path_points_3d(points: np.ndarray) -> list[Segment3D]:
    """Build open-path segments from path point coordinates."""

    point_count = points.shape[0]
    return [
        (
            (float(points[index][0]), float(points[index][1]), float(points[index][2])),
            (
                float(points[index + 1][0]),
                float(points[index + 1][1]),
                float(points[index + 1][2]),
            ),
        )
        for index in range(max(0, point_count - 1))
    ]
