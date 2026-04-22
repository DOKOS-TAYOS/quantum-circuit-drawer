"""Compatibility facade for managed 3D page-window helpers."""

from __future__ import annotations

from .managed.page_window_3d import (
    _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO,
    Managed3DPageWindowState,
    _projected_scene_aspect_ratio,
    configure_3d_page_window,
    windowed_3d_page_ranges,
    windowed_3d_page_scenes,
)

__all__ = [
    "_MIN_3D_PAGE_PROJECTED_ASPECT_RATIO",
    "_projected_scene_aspect_ratio",
    "Managed3DPageWindowState",
    "configure_3d_page_window",
    "windowed_3d_page_ranges",
    "windowed_3d_page_scenes",
]
