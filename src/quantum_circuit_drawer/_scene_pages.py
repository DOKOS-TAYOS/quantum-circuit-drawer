"""Compatibility facade for page-scene helpers."""

from __future__ import annotations

from .drawing.pages import (
    LayoutScene,
    Protocol,
    ScenePage,
    TypeVar,
    _items_for_page,
    _SceneColumnItem,
    _SceneColumnItemLike,
    annotations,
    replace,
    single_page_scene,
    single_page_scenes,
)

__all__ = [
    "LayoutScene",
    "Protocol",
    "ScenePage",
    "TypeVar",
    "_SceneColumnItem",
    "_SceneColumnItemLike",
    "_items_for_page",
    "annotations",
    "replace",
    "single_page_scene",
    "single_page_scenes",
]
