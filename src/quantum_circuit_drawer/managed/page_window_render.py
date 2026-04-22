"""Managed fixed-page-window render lifecycle for 2D rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..renderers._matplotlib_figure import (
    clear_hover_state,
    clear_text_scaling_state,
    set_viewport_width,
)
from ..renderers._matplotlib_hover import _HoverTarget2D, attach_hover
from ..renderers._matplotlib_page_projection import _ProjectedPage
from ..renderers.matplotlib_primitives import (
    _build_gate_text_fitting_context,
    finalize_axes,
    prepare_axes,
    trim_gate_text_fit_cache,
)
from .page_window_windowing import (
    _project_page,
    _visible_page_indexes,
    _window_page,
    _window_scene,
)
from .zoom import configure_zoom_text_scaling

if TYPE_CHECKING:
    from .page_window import Managed2DPageWindowState


def _render_current_window(state: Managed2DPageWindowState) -> None:
    clear_hover_state(state.axes)
    clear_text_scaling_state(state.axes)
    state.axes.clear()

    window_scene = _window_scene(state)
    state.window_scene = window_scene
    state.figure.patch.set_facecolor(window_scene.style.theme.figure_facecolor)
    prepare_axes(state.axes, window_scene)
    gate_text_context = _build_gate_text_fitting_context(state.axes, window_scene)
    hover_targets: list[_HoverTarget2D] = []

    for window_index, page_index in enumerate(_visible_page_indexes(state)):
        projected_page = _projected_page_for_index(state, page_index)
        window_page = _window_page(state, page_index=page_index, window_index=window_index)
        state.renderer._draw_page(
            state.axes,
            window_scene,
            window_page,
            projected_page,
            gate_text_context=gate_text_context,
            gate_text_cache=state.text_fit_cache,
            hover_targets=hover_targets,
        )

    if window_scene.hover.enabled and hover_targets:
        attach_hover(
            state.axes,
            window_scene.hover,
            hover_targets,
            theme=window_scene.style.theme,
        )

    finalize_axes(state.axes)

    configure_zoom_text_scaling(state.axes, scene=window_scene)
    set_viewport_width(state.figure, viewport_width=window_scene.width)
    trim_gate_text_fit_cache(state.text_fit_cache)
    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _projected_page_for_index(
    state: Managed2DPageWindowState,
    page_index: int,
) -> _ProjectedPage:
    cached_entry = state.page_cache.get(page_index)
    if cached_entry is not None:
        return cached_entry

    projected_page = _project_page(state.scene, page_index)
    state.page_cache[page_index] = projected_page
    return projected_page
