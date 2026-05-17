"""Helpers for deriving page-specific scene views."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol, TypeVar

from ..layout.scene import LayoutScene, SceneGroupHighlight, ScenePage


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
        wire_fold_markers=scene.wire_fold_markers,
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
        group_highlights=_group_highlights_for_page(scene.group_highlights, page=page),
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


def _group_highlights_for_page(
    highlights: tuple[SceneGroupHighlight, ...],
    *,
    page: ScenePage,
) -> tuple[SceneGroupHighlight, ...]:
    return tuple(
        projected_highlight
        for highlight in highlights
        if (projected_highlight := _project_group_highlight_for_page(highlight, page=page))
        is not None
    )


def _project_group_highlight_for_page(
    highlight: SceneGroupHighlight,
    *,
    page: ScenePage,
) -> SceneGroupHighlight | None:
    start_column = (
        highlight.start_column if highlight.start_column is not None else highlight.column
    )
    end_column = highlight.end_column if highlight.end_column is not None else highlight.column
    if end_column < page.start_column or start_column > page.end_column:
        return None

    x_min = highlight.x - (highlight.width / 2.0)
    x_max = highlight.x + (highlight.width / 2.0)
    continues_left = start_column < page.start_column
    continues_right = end_column > page.end_column
    clipped_x_min = page.content_x_start if continues_left else x_min
    clipped_x_max = page.content_x_end if continues_right else x_max
    if clipped_x_max <= clipped_x_min:
        clipped_x_min = page.content_x_start
        clipped_x_max = page.content_x_end

    return replace(
        highlight,
        column=max(start_column, page.start_column),
        x=(clipped_x_min + clipped_x_max) / 2.0,
        width=clipped_x_max - clipped_x_min,
        continues_left=continues_left,
        continues_right=continues_right,
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
