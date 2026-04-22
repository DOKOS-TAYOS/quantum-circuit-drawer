"""Helpers for deriving page-specific scene views."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, TypeVar

from ..layout.scene import LayoutScene, ScenePage


class _SceneColumnItemLike(Protocol):
    """Protocol for scene items that track a ``column`` index."""

    column: int


_SceneColumnItem = TypeVar("_SceneColumnItem", bound=_SceneColumnItemLike)


def single_page_scene(scene: LayoutScene, page_index: int) -> LayoutScene:
    """Return a 2D scene containing only one wrapped page."""

    page = scene.pages[page_index]
    shared_content_width = max(
        (wrapped_page.content_width for wrapped_page in scene.pages),
        default=page.content_width,
    )
    page_count_for_text_scale = (
        scene.page_count_for_text_scale
        if scene.page_count_for_text_scale is not None
        else len(scene.pages)
    )
    return LayoutScene(
        width=scene.style.margin_left + shared_content_width + scene.style.margin_right,
        height=scene.page_height,
        page_height=scene.page_height,
        style=scene.style,
        wires=scene.wires,
        gates=_items_for_page(scene.gates, page=page),
        gate_annotations=_items_for_page(scene.gate_annotations, page=page),
        controls=_items_for_page(scene.controls, page=page),
        connections=_items_for_page(scene.connections, page=page),
        swaps=_items_for_page(scene.swaps, page=page),
        barriers=_items_for_page(scene.barriers, page=page),
        measurements=_items_for_page(scene.measurements, page=page),
        texts=scene.texts,
        pages=(
            replace(
                page,
                index=0,
                y_offset=0.0,
                content_x_end=page.content_x_start + shared_content_width,
                content_width=shared_content_width,
            ),
        ),
        hover=scene.hover,
        wire_y_positions=dict(scene.wire_y_positions),
        page_count_for_text_scale=page_count_for_text_scale,
    )


def single_page_scenes(scene: LayoutScene) -> tuple[LayoutScene, ...]:
    """Return one derived scene per wrapped page."""

    return tuple(single_page_scene(scene, page_index) for page_index in range(len(scene.pages)))


def _items_for_page(
    items: tuple[_SceneColumnItem, ...],
    *,
    page: ScenePage,
) -> tuple[_SceneColumnItem, ...]:
    return tuple(item for item in items if page.start_column <= item.column <= page.end_column)


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
