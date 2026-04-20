"""Managed fixed-page-window slicing helpers for 2D rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..drawing.pages import _items_for_page
from ..layout.scene import LayoutScene, ScenePage
from ..renderers._matplotlib_page_projection import _ProjectedPage

if TYPE_CHECKING:
    from .page_window import Managed2DPageWindowState


def _clamp_page_index(requested_page: int, total_pages: int) -> int:
    return min(max(1, requested_page), total_pages) - 1


def _clamp_visible_page_count(
    requested_visible_pages: int,
    *,
    total_pages: int,
    start_page: int,
) -> int:
    max_visible_pages = max(1, total_pages - start_page)
    return min(max(1, requested_visible_pages), max_visible_pages)


def _window_scene(state: Managed2DPageWindowState) -> LayoutScene:
    visible_pages = tuple(_window_pages(state))
    return LayoutScene(
        width=_visible_page_width(state),
        height=state.scene.page_height
        + (
            (len(visible_pages) - 1)
            * (state.scene.page_height + state.scene.style.page_vertical_gap)
        ),
        page_height=state.scene.page_height,
        style=state.scene.style,
        wires=state.scene.wires,
        gates=(),
        gate_annotations=(),
        controls=(),
        connections=(),
        swaps=(),
        barriers=(),
        measurements=(),
        texts=state.scene.texts,
        pages=visible_pages,
        hover=state.scene.hover,
        wire_y_positions=dict(state.scene.wire_y_positions),
        page_count_for_text_scale=state.total_pages,
    )


def _window_pages(state: Managed2DPageWindowState) -> tuple[ScenePage, ...]:
    visible_pages: list[ScenePage] = []
    for window_index, page_index in enumerate(_visible_page_indexes(state)):
        visible_pages.append(_window_page(state, page_index=page_index, window_index=window_index))
    return tuple(visible_pages)


def _visible_page_indexes(state: Managed2DPageWindowState) -> range:
    return range(state.start_page, state.start_page + state.visible_page_count)


def _visible_page_width(state: Managed2DPageWindowState) -> float:
    return max(
        (
            state.scene.style.margin_left
            + state.scene.pages[page_index].content_width
            + state.scene.style.margin_right
            for page_index in _visible_page_indexes(state)
        ),
        default=state.scene.width,
    )


def _window_page(
    state: Managed2DPageWindowState,
    *,
    page_index: int,
    window_index: int,
) -> ScenePage:
    source_page = state.scene.pages[page_index]
    return ScenePage(
        index=window_index,
        start_column=source_page.start_column,
        end_column=source_page.end_column,
        content_x_start=source_page.content_x_start,
        content_x_end=source_page.content_x_end,
        content_width=source_page.content_width,
        y_offset=window_index * (state.scene.page_height + state.scene.style.page_vertical_gap),
    )


def _project_page(scene: LayoutScene, page_index: int) -> _ProjectedPage:
    page = scene.pages[page_index]
    return _ProjectedPage(
        barriers=_items_for_page(scene.barriers, page=page),
        connections=_items_for_page(scene.connections, page=page),
        gates=_items_for_page(scene.gates, page=page),
        gate_annotations=_items_for_page(scene.gate_annotations, page=page),
        measurements=_items_for_page(scene.measurements, page=page),
        controls=_items_for_page(scene.controls, page=page),
        swaps=_items_for_page(scene.swaps, page=page),
    )
