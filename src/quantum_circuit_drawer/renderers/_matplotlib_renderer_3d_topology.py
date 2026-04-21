"""Topology helpers for the 3D Matplotlib renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # type: ignore[import-untyped]

from ..layout.scene_3d import LayoutScene3D
from ._matplotlib_renderer_3d_geometry import point_array_3d

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]


def topology_plane_points_3d(scene: LayoutScene3D) -> np.ndarray:
    return point_array_3d(
        [
            (x_value, y_value, plane.z)
            for plane in scene.topology_planes
            for x_value, y_value in (
                (plane.x_min, plane.y_min),
                (plane.x_max, plane.y_min),
                (plane.x_max, plane.y_max),
                (plane.x_min, plane.y_max),
            )
        ]
    )


def draw_topology_planes_3d(axes: Axes3D, scene: LayoutScene3D) -> None:
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
