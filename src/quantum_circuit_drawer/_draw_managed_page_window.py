"""Managed fixed-page-window helpers for 2D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ._draw_managed_slider import _style_text_box, circuit_window
from ._draw_managed_viewport import compute_paged_scene
from .layout.scene import LayoutScene, ScenePage
from .renderers._matplotlib_figure import (
    clear_hover_state,
    clear_text_scaling_state,
    set_viewport_width,
)
from .renderers._matplotlib_hover import _HoverTarget2D, attach_hover
from .renderers._matplotlib_page_projection import _ProjectedPage, project_pages
from .renderers.matplotlib_primitives import (
    _build_gate_text_fitting_context,
    finalize_axes,
    prepare_axes,
)
from .renderers.matplotlib_renderer import MatplotlibRenderer
from .typing import LayoutEngineLike

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import TextBox

    from .ir.circuit import CircuitIR

_MAIN_AXES_BOUNDS = (0.02, 0.18, 0.96, 0.8)
_PAGE_BOX_BOUNDS = (0.18, 0.045, 0.09, 0.055)
_VISIBLE_PAGES_BOX_BOUNDS = (0.54, 0.045, 0.09, 0.055)
_PAGE_LABEL_POSITION = (0.08, 0.072)
_PAGE_SUFFIX_POSITION = (0.285, 0.072)
_VISIBLE_LABEL_POSITION = (0.39, 0.072)
_VISIBLE_SUFFIX_POSITION = (0.645, 0.072)


@dataclass(frozen=True, slots=True)
class _PageWindowCacheEntry:
    scene: LayoutScene
    projected_page: _ProjectedPage


@dataclass(slots=True)
class Managed2DPageWindowState:
    """Managed fixed-page-window state attached to one figure."""

    figure: Figure
    axes: Axes
    circuit: CircuitIR
    layout_engine: LayoutEngineLike
    renderer: MatplotlibRenderer
    scene: LayoutScene
    effective_page_width: float
    total_pages: int
    start_page: int
    visible_page_count: int
    page_cache: dict[int, _PageWindowCacheEntry] = field(default_factory=dict)
    page_box: TextBox | None = None
    visible_pages_box: TextBox | None = None
    page_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
    page_suffix_text: Text | None = None
    visible_suffix_text: Text | None = None
    is_syncing_inputs: bool = False


def configure_page_window(
    *,
    figure: Figure,
    axes: Axes,
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    renderer: MatplotlibRenderer,
    scene: LayoutScene,
    effective_page_width: float,
    set_page_window: Callable[[Figure, object], None],
) -> Managed2DPageWindowState:
    """Attach fixed page-window controls and render the initial visible window."""

    total_pages = max(1, len(scene.pages))
    state = Managed2DPageWindowState(
        figure=figure,
        axes=axes,
        circuit=circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        scene=scene,
        effective_page_width=effective_page_width,
        total_pages=total_pages,
        start_page=0,
        visible_page_count=1,
    )
    set_page_window(figure, state)
    _attach_controls(state)
    _render_current_window(state)
    _sync_inputs(state)
    return state


def _attach_controls(state: Managed2DPageWindowState) -> None:
    from matplotlib.widgets import TextBox

    theme = state.scene.style.theme
    state.axes.set_position(_MAIN_AXES_BOUNDS)

    page_axes = state.figure.add_axes(_PAGE_BOX_BOUNDS, facecolor=theme.axes_facecolor)
    page_box = TextBox(
        page_axes,
        "",
        initial="1",
        color=theme.axes_facecolor,
        hovercolor=theme.figure_facecolor,
        textalignment="center",
    )
    _style_text_box(page_box, text_color=theme.text_color)
    page_box.on_submit(lambda text: _handle_page_submit(state, text))

    visible_pages_axes = state.figure.add_axes(
        _VISIBLE_PAGES_BOX_BOUNDS,
        facecolor=theme.axes_facecolor,
    )
    visible_pages_box = TextBox(
        visible_pages_axes,
        "",
        initial="1",
        color=theme.axes_facecolor,
        hovercolor=theme.figure_facecolor,
        textalignment="center",
    )
    _style_text_box(visible_pages_box, text_color=theme.text_color)
    visible_pages_box.on_submit(lambda text: _handle_visible_pages_submit(state, text))

    state.page_box = page_box
    state.visible_pages_box = visible_pages_box
    state.page_axes = page_axes
    state.visible_pages_axes = visible_pages_axes
    state.page_suffix_text = state.figure.text(
        _PAGE_SUFFIX_POSITION[0],
        _PAGE_SUFFIX_POSITION[1],
        f"/ {state.total_pages}",
        color=theme.text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )
    state.visible_suffix_text = state.figure.text(
        _VISIBLE_SUFFIX_POSITION[0],
        _VISIBLE_SUFFIX_POSITION[1],
        f"/ {state.total_pages}",
        color=theme.text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )
    state.figure.text(
        _PAGE_LABEL_POSITION[0],
        _PAGE_LABEL_POSITION[1],
        "Page",
        color=theme.text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )
    state.figure.text(
        _VISIBLE_LABEL_POSITION[0],
        _VISIBLE_LABEL_POSITION[1],
        "Visible",
        color=theme.text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )


def _handle_page_submit(state: Managed2DPageWindowState, text: str) -> None:
    if state.is_syncing_inputs:
        return

    try:
        requested_page = int(text.strip())
    except ValueError:
        _sync_inputs(state)
        return

    state.start_page = _clamp_page_index(requested_page, state.total_pages)
    state.visible_page_count = _clamp_visible_page_count(
        state.visible_page_count,
        total_pages=state.total_pages,
        start_page=state.start_page,
    )
    _render_current_window(state)
    _sync_inputs(state)


def _handle_visible_pages_submit(state: Managed2DPageWindowState, text: str) -> None:
    if state.is_syncing_inputs:
        return

    try:
        requested_visible_pages = int(text.strip())
    except ValueError:
        _sync_inputs(state)
        return

    state.visible_page_count = _clamp_visible_page_count(
        requested_visible_pages,
        total_pages=state.total_pages,
        start_page=state.start_page,
    )
    _render_current_window(state)
    _sync_inputs(state)


def _sync_inputs(state: Managed2DPageWindowState) -> None:
    if state.page_box is None or state.visible_pages_box is None:
        return

    state.is_syncing_inputs = True
    try:
        state.page_box.set_val(str(state.start_page + 1))
        state.visible_pages_box.set_val(str(state.visible_page_count))
    finally:
        state.is_syncing_inputs = False


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


def _render_current_window(state: Managed2DPageWindowState) -> None:
    clear_hover_state(state.axes)
    clear_text_scaling_state(state.axes)
    state.axes.clear()

    window_scene = _window_scene(state)
    state.figure.patch.set_facecolor(window_scene.style.theme.figure_facecolor)
    prepare_axes(state.axes, window_scene)
    gate_text_context = _build_gate_text_fitting_context(state.axes, window_scene)
    gate_text_cache: dict[tuple[object, float, float], float] = {}
    hover_targets: list[_HoverTarget2D] = []

    for window_index, page_index in enumerate(_visible_page_indexes(state)):
        cache_entry = _cache_entry_for_page(state, page_index)
        source_page = state.scene.pages[page_index]
        window_page = ScenePage(
            index=window_index,
            start_column=source_page.start_column,
            end_column=source_page.end_column,
            content_x_start=source_page.content_x_start,
            content_x_end=source_page.content_x_end,
            content_width=source_page.content_width,
            y_offset=window_index
            * (window_scene.page_height + window_scene.style.page_vertical_gap),
        )
        state.renderer._draw_page(
            state.axes,
            window_scene,
            window_page,
            cache_entry.projected_page,
            gate_text_context=gate_text_context,
            gate_text_cache=gate_text_cache,
            hover_targets=hover_targets,
        )

    if window_scene.hover.enabled and hover_targets:
        attach_hover(state.axes, window_scene.hover, hover_targets)

    finalize_axes(state.axes, window_scene)
    from ._draw_managed import configure_zoom_text_scaling

    configure_zoom_text_scaling(state.axes, scene=window_scene)
    set_viewport_width(state.figure, viewport_width=window_scene.width)
    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _window_scene(state: Managed2DPageWindowState) -> LayoutScene:
    visible_pages = tuple(_window_pages(state))
    return LayoutScene(
        width=state.scene.width,
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
        source_page = state.scene.pages[page_index]
        visible_pages.append(
            ScenePage(
                index=window_index,
                start_column=source_page.start_column,
                end_column=source_page.end_column,
                content_x_start=source_page.content_x_start,
                content_x_end=source_page.content_x_end,
                content_width=source_page.content_width,
                y_offset=window_index
                * (state.scene.page_height + state.scene.style.page_vertical_gap),
            )
        )
    return tuple(visible_pages)


def _visible_page_indexes(state: Managed2DPageWindowState) -> range:
    return range(state.start_page, state.start_page + state.visible_page_count)


def _cache_entry_for_page(
    state: Managed2DPageWindowState,
    page_index: int,
) -> _PageWindowCacheEntry:
    cached_entry = state.page_cache.get(page_index)
    if cached_entry is not None:
        return cached_entry

    source_page = state.scene.pages[page_index]
    page_circuit = circuit_window(
        state.circuit,
        start_column=source_page.start_column,
        window_size=(source_page.end_column - source_page.start_column + 1),
    )
    page_scene = compute_paged_scene(
        page_circuit,
        state.layout_engine,
        state.scene.style,
        hover_enabled=state.scene.hover.enabled,
    )
    page_scene.hover = state.scene.hover
    projected_pages = project_pages(page_scene)
    projected_page = projected_pages[0]
    cache_entry = _PageWindowCacheEntry(scene=page_scene, projected_page=projected_page)
    state.page_cache[page_index] = cache_entry
    return cache_entry
