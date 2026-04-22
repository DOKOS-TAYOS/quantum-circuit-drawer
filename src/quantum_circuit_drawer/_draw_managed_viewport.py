"""Compatibility facade for managed viewport helpers."""

from __future__ import annotations

from .managed.viewport import (
    Axes,
    CircuitIR,
    DrawStyle,
    Figure,
    LayoutEngineLike,
    LayoutScene,
    SubFigure,
    _figure_size_inches,
    _scene_aspect_ratio_for_size,
    _viewport_scene_score_for_size,
    annotations,
    axes_viewport_pixels,
    axes_viewport_ratio,
    build_continuous_slider_scene,
    compute_paged_scene,
    math,
    page_window_adaptive_paged_scene,
    scene_aspect_ratio,
    viewport_adaptive_paged_scene,
    viewport_scene_score,
)

__all__ = [
    "Axes",
    "CircuitIR",
    "DrawStyle",
    "Figure",
    "LayoutEngineLike",
    "LayoutScene",
    "SubFigure",
    "_figure_size_inches",
    "_scene_aspect_ratio_for_size",
    "_viewport_scene_score_for_size",
    "annotations",
    "axes_viewport_pixels",
    "axes_viewport_ratio",
    "build_continuous_slider_scene",
    "compute_paged_scene",
    "math",
    "page_window_adaptive_paged_scene",
    "scene_aspect_ratio",
    "viewport_adaptive_paged_scene",
    "viewport_scene_score",
]
