"""Marker, text, and hover helpers for the 3D Matplotlib renderer."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from matplotlib.artist import Artist
from matplotlib.collections import PathCollection
from matplotlib.transforms import Affine2D, IdentityTransform
from mpl_toolkits.mplot3d.art3d import Line3DCollection  # type: ignore[import-untyped]

from ..layout.scene_3d import LayoutScene3D, MarkerStyle3D, SceneGate3D
from ..style import (
    resolved_connection_line_width,
    resolved_measurement_line_width,
    resolved_topology_edge_line_width,
)
from ._matplotlib_renderer_3d_hover import attach_hover_3d
from ._matplotlib_renderer_3d_text import (
    _aligned_text_path,
    _TextPathCacheKey,
    _visible_3d_text_value,
)
from ._render_support import backend_supports_interaction, figure_backend_name

if TYPE_CHECKING:
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ._matplotlib_renderer_3d_geometry import Segment3D, _RenderContext3D
    from .matplotlib_renderer_3d import MatplotlibRenderer3D


def marker_geometry_points_3d(scene: LayoutScene3D) -> np.ndarray:
    points: list[tuple[float, float, float]] = []
    for marker in scene.markers:
        if marker.style is MarkerStyle3D.SWAP:
            size = marker.size
            points.extend(
                (
                    (marker.center.x - size, marker.center.y - size, marker.center.z),
                    (marker.center.x + size, marker.center.y + size, marker.center.z),
                    (marker.center.x - size, marker.center.y + size, marker.center.z),
                    (marker.center.x + size, marker.center.y - size, marker.center.z),
                )
            )
            continue
        points.append((marker.center.x, marker.center.y, marker.center.z))
    return np.asarray(points, dtype=float) if points else np.empty((0, 3), dtype=float)


def text_geometry_points_3d(scene: LayoutScene3D) -> np.ndarray:
    points = [(text.position.x, text.position.y, text.position.z) for text in scene.texts]
    return np.asarray(points, dtype=float) if points else np.empty((0, 3), dtype=float)


def draw_markers_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
) -> list[tuple[Artist, str]]:
    if scene.hover_enabled:
        return draw_markers_with_hover_3d(renderer, axes, scene)
    return draw_markers_batched_3d(axes, scene)


def draw_markers_with_hover_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
) -> list[tuple[Artist, str]]:
    del renderer
    hover_targets: list[tuple[Artist, str]] = []
    for marker in scene.markers:
        if marker.style is MarkerStyle3D.TOPOLOGY_NODE:
            axes.scatter(
                [marker.center.x],
                [marker.center.y],
                [marker.center.z],
                s=marker.size * 320.0,
                facecolors=scene.style.theme.axes_facecolor,
                edgecolors=scene.style.theme.topology_edge_color or scene.style.theme.wire_color,
                linewidths=max(1.0, resolved_topology_edge_line_width(scene.style)),
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
                c=scene.style.theme.control_color or scene.style.theme.control_connection_color,
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
            linewidths=resolved_connection_line_width(scene.style),
        )
        collection.set_zorder(3.1)
        axes.add_collection3d(collection)
    return hover_targets


def draw_markers_batched_3d(
    axes: Axes3D,
    scene: LayoutScene3D,
) -> list[tuple[Artist, str]]:
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
            edgecolors=scene.style.theme.topology_edge_color or scene.style.theme.wire_color,
            linewidths=max(1.0, resolved_topology_edge_line_width(scene.style)),
            depthshade=False,
            zorder=3.2,
        )

    control_markers = [marker for marker in scene.markers if marker.style is MarkerStyle3D.CONTROL]
    if control_markers:
        axes.scatter(
            [marker.center.x for marker in control_markers],
            [marker.center.y for marker in control_markers],
            [marker.center.z for marker in control_markers],
            s=[marker.size * 18.0 for marker in control_markers],
            c=scene.style.theme.control_color or scene.style.theme.control_connection_color,
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
            linewidths=resolved_connection_line_width(scene.style),
        )
        collection.set_zorder(3.1)
        axes.add_collection3d(collection)
    return []


def draw_measurement_symbols_batched_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    gates: list[SceneGate3D],
    scene: LayoutScene3D,
) -> None:
    arc_segments: list[Segment3D] = []
    pointer_segments: list[Segment3D] = []

    for gate in gates:
        top_z = gate.center.z + (gate.size_z * 0.53)
        theta = np.linspace(np.pi, 2.0 * np.pi, 32)
        arc_points = np.column_stack(
            (
                gate.center.x + (gate.size_x * 0.26 * np.cos(theta)),
                gate.center.y - (gate.size_y * 0.06) + (gate.size_y * 0.24 * np.sin(theta)),
                np.full_like(theta, top_z),
            )
        )
        arc_segments.extend(renderer._segments_for_path_points(arc_points))
        pointer_segments.append(
            (
                (
                    gate.center.x - (gate.size_x * 0.04),
                    gate.center.y - (gate.size_y * 0.12),
                    top_z,
                ),
                (
                    gate.center.x + (gate.size_x * 0.16),
                    gate.center.y + (gate.size_y * 0.16),
                    top_z,
                ),
            )
        )

    if arc_segments:
        arc_collection = Line3DCollection(
            arc_segments,
            colors=scene.style.theme.measurement_color,
            linewidths=resolved_measurement_line_width(scene.style),
        )
        arc_collection.set_capstyle("round")
        arc_collection.set_zorder(3.6)
        axes.add_collection3d(arc_collection)
    if pointer_segments:
        pointer_collection = Line3DCollection(
            pointer_segments,
            colors=scene.style.theme.measurement_color,
            linewidths=resolved_measurement_line_width(scene.style),
        )
        pointer_collection.set_capstyle("round")
        pointer_collection.set_zorder(3.6)
        axes.add_collection3d(pointer_collection)


def draw_texts_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    render_context: _RenderContext3D,
    managed_render: bool,
    batched_artists_attr: str,
    batched_artist_gid: str,
    text_layer_zorder: float,
) -> None:
    if renderer._should_batch_offscreen_texts(
        axes,
        scene,
        managed_render=managed_render,
    ):
        draw_texts_batched_offscreen_3d(
            renderer,
            axes,
            scene,
            render_context=render_context,
            batched_artists_attr=batched_artists_attr,
            batched_artist_gid=batched_artist_gid,
            text_layer_zorder=text_layer_zorder,
        )
        return
    draw_texts_standard_3d(axes, scene)


def draw_texts_standard_3d(axes: Axes3D, scene: LayoutScene3D) -> None:
    for text in scene.texts:
        visible_text = _visible_3d_text_value(text.text, role=text.role, scene=scene)
        axes.text(
            text.position.x,
            text.position.y,
            text.position.z,
            visible_text,
            ha=text.ha,
            va=text.va,
            multialignment=text.ha,
            fontsize=text.font_size or scene.style.font_size,
            color=scene.style.theme.classical_wire_color,
        )


def draw_texts_batched_offscreen_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    render_context: _RenderContext3D,
    batched_artists_attr: str,
    batched_artist_gid: str,
    text_layer_zorder: float,
) -> None:
    if not scene.texts:
        setattr(axes, batched_artists_attr, ())
        return

    projected_positions = renderer._projected_display_points(
        axes,
        np.array(
            [(text.position.x, text.position.y, text.position.z) for text in scene.texts],
            dtype=float,
        ),
        render_context=render_context,
    )
    grouped_offsets: dict[_TextPathCacheKey, list[tuple[float, float]]] = {}
    for text, projected_position in zip(scene.texts, projected_positions, strict=True):
        visible_text = _visible_3d_text_value(text.text, role=text.role, scene=scene)
        text_key = (
            visible_text,
            float(text.font_size or scene.style.font_size),
            text.ha,
            text.va,
        )
        grouped_offsets.setdefault(text_key, []).append(
            (
                float(projected_position[0]),
                float(projected_position[1]),
            )
        )

    display_scale = axes.figure.dpi / 72.0
    text_artists: list[Artist] = []
    for text_key, offsets in grouped_offsets.items():
        collection = PathCollection(
            [_aligned_text_path(text_key)],
            offsets=np.asarray(offsets, dtype=float),
            transOffset=IdentityTransform(),
            facecolors=scene.style.theme.classical_wire_color,
            edgecolors="none",
        )
        collection.set_transform(Affine2D().scale(display_scale))
        collection.set_clip_box(axes.bbox)
        collection.set_clip_on(True)
        collection.set_gid(batched_artist_gid)
        collection.set_zorder(text_layer_zorder)
        axes.figure.add_artist(collection)
        text_artists.append(collection)

    setattr(axes, batched_artists_attr, tuple(text_artists))


def should_batch_offscreen_texts_3d(
    renderer: MatplotlibRenderer3D,
    axes: Axes3D,
    scene: LayoutScene3D,
    *,
    managed_render: bool,
) -> bool:
    if scene.hover_enabled or not scene.texts:
        return False
    if not managed_render and renderer._managed_viewport_bounds(axes) is None:
        return False
    return not backend_supports_interaction(figure_backend_name(axes.figure))


def clear_batched_text_artists_3d(
    axes: Axes3D,
    *,
    batched_artists_attr: str,
) -> None:
    existing_artists = getattr(axes, batched_artists_attr, ())
    if not isinstance(existing_artists, tuple):
        setattr(axes, batched_artists_attr, ())
        return

    for artist in existing_artists:
        if not isinstance(artist, Artist):
            continue
        try:
            artist.remove()
        except (NotImplementedError, ValueError):
            continue
    setattr(axes, batched_artists_attr, ())


def attach_hover_targets_3d(
    axes: Axes3D,
    scene: LayoutScene3D,
    hover_targets: list[tuple[Artist, str]],
) -> None:
    attach_hover_3d(
        axes,
        hover_targets=hover_targets,
        hover_facecolor=scene.style.theme.hover_facecolor,
        hover_edgecolor=scene.style.theme.hover_edgecolor,
        hover_text_color=scene.style.theme.hover_text_color,
    )
