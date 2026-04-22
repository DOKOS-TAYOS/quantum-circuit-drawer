"""Compatibility facade for managed zoom helpers."""

from __future__ import annotations

from .managed.zoom import (
    Annotation,
    Axes,
    Callable,
    Event,
    LayoutScene,
    Text,
    _apply_text_artist_scale,
    _coerce_font_size,
    annotations,
    configure_zoom_text_scaling,
    current_text_scale,
    current_view_size,
    math,
)

__all__ = [
    "Annotation",
    "Axes",
    "Callable",
    "Event",
    "LayoutScene",
    "Text",
    "_apply_text_artist_scale",
    "_coerce_font_size",
    "annotations",
    "configure_zoom_text_scaling",
    "current_text_scale",
    "current_view_size",
    "math",
]
