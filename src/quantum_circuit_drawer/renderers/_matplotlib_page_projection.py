"""Helpers for projecting scene primitives onto wrapped Matplotlib pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from ..layout.scene import (
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneGroupHighlight,
    SceneMeasurement,
    ScenePage,
    SceneSwap,
)


@dataclass(frozen=True, slots=True)
class _ProjectedPage:
    barriers: tuple[SceneBarrier, ...]
    connections: tuple[SceneConnection, ...]
    gates: tuple[SceneGate, ...]
    gate_annotations: tuple[SceneGateAnnotation, ...]
    group_highlights: tuple[SceneGroupHighlight, ...]
    measurements: tuple[SceneMeasurement, ...]
    controls: tuple[SceneControl, ...]
    swaps: tuple[SceneSwap, ...]


_SceneColumnItem = TypeVar(
    "_SceneColumnItem",
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneGroupHighlight,
    SceneMeasurement,
    SceneSwap,
)


def projection_cache_key(scene: LayoutScene) -> tuple[object, ...]:
    """Return a stable cache key for one scene's projected-page structure."""

    return (
        id(scene),
        tuple(
            (
                page.index,
                page.start_column,
                page.end_column,
                round(page.content_width, 9),
                round(page.y_offset, 9),
            )
            for page in scene.pages
        ),
    )


def project_pages(scene: LayoutScene) -> tuple[_ProjectedPage, ...]:
    """Bucket each scene primitive into its rendered page."""

    page_index_lookup = page_index_by_column(scene.pages)
    page_count = len(scene.pages)
    barriers = bucket_by_page(scene.barriers, page_index_lookup, page_count)
    connections = bucket_by_page(scene.connections, page_index_lookup, page_count)
    gates = bucket_by_page(scene.gates, page_index_lookup, page_count)
    gate_annotations = bucket_by_page(scene.gate_annotations, page_index_lookup, page_count)
    group_highlights = bucket_by_page(scene.group_highlights, page_index_lookup, page_count)
    measurements = bucket_by_page(scene.measurements, page_index_lookup, page_count)
    controls = bucket_by_page(scene.controls, page_index_lookup, page_count)
    swaps = bucket_by_page(scene.swaps, page_index_lookup, page_count)
    return tuple(
        _ProjectedPage(
            barriers=barriers[page_index],
            connections=connections[page_index],
            gates=gates[page_index],
            gate_annotations=gate_annotations[page_index],
            group_highlights=group_highlights[page_index],
            measurements=measurements[page_index],
            controls=controls[page_index],
            swaps=swaps[page_index],
        )
        for page_index in range(page_count)
    )


def page_index_by_column(pages: tuple[ScenePage, ...]) -> tuple[int, ...]:
    """Return the page index for every column in the scene."""

    if not pages:
        return (0,)
    max_column = max(page.end_column for page in pages)
    page_indexes = [0] * (max_column + 1)
    for page_position, page in enumerate(pages):
        for column in range(page.start_column, page.end_column + 1):
            page_indexes[column] = page_position
    return tuple(page_indexes)


def bucket_by_page(
    items: tuple[_SceneColumnItem, ...],
    page_index_lookup: tuple[int, ...],
    page_count: int,
) -> tuple[tuple[_SceneColumnItem, ...], ...]:
    """Group scene primitives by page without rescanning membership."""

    buckets: list[list[_SceneColumnItem]] = [[] for _ in range(page_count)]
    for item in items:
        buckets[page_index_lookup[item.column]].append(item)
    return tuple(tuple(bucket) for bucket in buckets)


def page_x_offset(page: ScenePage, scene: LayoutScene) -> float:
    """Return the x offset needed to render a page at the origin."""

    return scene.style.margin_left - page.content_x_start


def page_y_offset(page: ScenePage) -> float:
    """Return the vertical offset used for wrapped page rendering."""

    return page.y_offset
