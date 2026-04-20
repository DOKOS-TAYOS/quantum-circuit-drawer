"""Managed fixed-page-window helpers for 2D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ..drawing.pages import _items_for_page
from ..layout.scene import LayoutScene, ScenePage
from ..renderers._matplotlib_figure import (
    clear_hover_state,
    clear_text_scaling_state,
    set_viewport_width,
)
from ..renderers._matplotlib_hover import _HoverTarget2D, attach_hover
from ..renderers._matplotlib_page_projection import _ProjectedPage
from ..renderers.matplotlib_primitives import (
    _build_gate_text_fitting_context,
    _GateTextCache,
    finalize_axes,
    prepare_axes,
    trim_gate_text_fit_cache,
)
from ..renderers.matplotlib_renderer import MatplotlibRenderer
from ..typing import LayoutEngineLike
from .controls import _style_control_axes, _style_stepper_button, _style_text_box
from .ui_palette import ManagedUiPalette, managed_ui_palette

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import Button, TextBox

    from ..ir.circuit import CircuitIR

_MAIN_AXES_BOUNDS = (0.02, 0.18, 0.96, 0.8)
_PREVIOUS_PAGE_BUTTON_BOUNDS = (0.132, 0.05, 0.048, 0.06)
_PAGE_BOX_BOUNDS = (0.188, 0.05, 0.078, 0.06)
_NEXT_PAGE_BUTTON_BOUNDS = (0.274, 0.05, 0.048, 0.06)
_VISIBLE_PAGES_BOX_BOUNDS = (0.505, 0.05, 0.078, 0.06)
_VISIBLE_PAGES_DECREMENT_BOUNDS = (0.591, 0.05, 0.03, 0.028)
_VISIBLE_PAGES_INCREMENT_BOUNDS = (0.591, 0.082, 0.03, 0.028)
_PAGE_LABEL_POSITION = (0.075, 0.079)
_PAGE_SUFFIX_POSITION = (0.33, 0.079)
_VISIBLE_LABEL_POSITION = (0.392, 0.079)
_VISIBLE_SUFFIX_POSITION = (0.628, 0.079)


@dataclass(frozen=True, slots=True)
class _PageWindowCacheEntry:
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
    text_fit_cache: _GateTextCache = field(default_factory=dict)
    page_box: TextBox | None = None
    visible_pages_box: TextBox | None = None
    visible_pages_decrement_button: Button | None = None
    visible_pages_increment_button: Button | None = None
    previous_page_button: Button | None = None
    next_page_button: Button | None = None
    page_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
    visible_pages_decrement_axes: Axes | None = None
    visible_pages_increment_axes: Axes | None = None
    previous_page_button_axes: Axes | None = None
    next_page_button_axes: Axes | None = None
    page_suffix_text: Text | None = None
    visible_suffix_text: Text | None = None
    ui_palette: ManagedUiPalette | None = None
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
    ui_palette = managed_ui_palette(scene.style.theme)
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
        ui_palette=ui_palette,
    )
    set_page_window(figure, state)
    _attach_controls(state)
    _render_current_window(state)
    _sync_inputs(state)
    return state


def apply_page_window_axes_bounds(axes: Axes) -> None:
    """Pin page-window drawing axes above the control row."""

    axes.set_position(_MAIN_AXES_BOUNDS)


def _attach_controls(state: Managed2DPageWindowState) -> None:
    from matplotlib.widgets import Button, TextBox

    theme = state.scene.style.theme
    palette = state.ui_palette or managed_ui_palette(theme)
    apply_page_window_axes_bounds(state.axes)

    previous_page_button_axes = state.figure.add_axes(
        _PREVIOUS_PAGE_BUTTON_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(previous_page_button_axes, palette=palette)
    previous_page_button = Button(
        previous_page_button_axes,
        "\u2039",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    _style_button(previous_page_button, palette=palette)
    previous_page_button.on_clicked(lambda _: _step_page(state, delta=-1))

    page_axes = state.figure.add_axes(_PAGE_BOX_BOUNDS, facecolor=palette.surface_facecolor)
    _style_control_axes(page_axes, palette=palette)
    page_box = TextBox(
        page_axes,
        "",
        initial="1",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
        textalignment="center",
    )
    _style_text_box(
        page_box,
        text_color=palette.text_color,
        border_color=palette.surface_edgecolor,
        facecolor=palette.surface_facecolor,
    )
    page_box.on_submit(lambda text: _handle_page_submit(state, text))

    next_page_button_axes = state.figure.add_axes(
        _NEXT_PAGE_BUTTON_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(next_page_button_axes, palette=palette)
    next_page_button = Button(
        next_page_button_axes,
        "\u203a",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    _style_button(next_page_button, palette=palette)
    next_page_button.on_clicked(lambda _: _step_page(state, delta=1))

    visible_pages_axes = state.figure.add_axes(
        _VISIBLE_PAGES_BOX_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(visible_pages_axes, palette=palette)
    visible_pages_box = TextBox(
        visible_pages_axes,
        "",
        initial="1",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
        textalignment="center",
    )
    _style_text_box(
        visible_pages_box,
        text_color=palette.text_color,
        border_color=palette.surface_edgecolor,
        facecolor=palette.surface_facecolor,
    )
    visible_pages_box.on_submit(lambda text: _handle_visible_pages_submit(state, text))

    visible_pages_increment_axes = state.figure.add_axes(
        _VISIBLE_PAGES_INCREMENT_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(visible_pages_increment_axes, palette=palette)
    visible_pages_increment_button = Button(
        visible_pages_increment_axes,
        "\u25b4",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    _style_stepper_button(visible_pages_increment_button, palette=palette)
    visible_pages_increment_button.on_clicked(lambda _: _step_visible_pages(state, delta=1))

    visible_pages_decrement_axes = state.figure.add_axes(
        _VISIBLE_PAGES_DECREMENT_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    _style_control_axes(visible_pages_decrement_axes, palette=palette)
    visible_pages_decrement_button = Button(
        visible_pages_decrement_axes,
        "\u25be",
        color=palette.surface_facecolor,
        hovercolor=palette.surface_hover_facecolor,
    )
    _style_stepper_button(visible_pages_decrement_button, palette=palette)
    visible_pages_decrement_button.on_clicked(lambda _: _step_visible_pages(state, delta=-1))

    state.page_box = page_box
    state.visible_pages_box = visible_pages_box
    state.visible_pages_decrement_button = visible_pages_decrement_button
    state.visible_pages_increment_button = visible_pages_increment_button
    state.previous_page_button = previous_page_button
    state.next_page_button = next_page_button
    state.page_axes = page_axes
    state.visible_pages_axes = visible_pages_axes
    state.visible_pages_decrement_axes = visible_pages_decrement_axes
    state.visible_pages_increment_axes = visible_pages_increment_axes
    state.previous_page_button_axes = previous_page_button_axes
    state.next_page_button_axes = next_page_button_axes
    state.page_suffix_text = state.figure.text(
        _PAGE_SUFFIX_POSITION[0],
        _PAGE_SUFFIX_POSITION[1],
        f"/ {state.total_pages}",
        color=palette.secondary_text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )
    state.visible_suffix_text = state.figure.text(
        _VISIBLE_SUFFIX_POSITION[0],
        _VISIBLE_SUFFIX_POSITION[1],
        f"/ {state.total_pages}",
        color=palette.secondary_text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )
    state.figure.text(
        _PAGE_LABEL_POSITION[0],
        _PAGE_LABEL_POSITION[1],
        "Page",
        color=palette.secondary_text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )
    state.figure.text(
        _VISIBLE_LABEL_POSITION[0],
        _VISIBLE_LABEL_POSITION[1],
        "Visible",
        color=palette.secondary_text_color,
        ha="left",
        va="center",
        fontsize=10.0,
    )
    _sync_navigation_button_states(state)


def _style_button(button: Button, *, palette: ManagedUiPalette) -> None:
    button.ax.set_facecolor(palette.surface_facecolor)
    button.label.set_color(palette.text_color)
    button.label.set_fontsize(12.0)
    button.label.set_fontweight("bold")
    button.ax.tick_params(
        left=False,
        bottom=False,
        labelleft=False,
        labelbottom=False,
    )
    for spine in button.ax.spines.values():
        spine.set_color(palette.surface_edgecolor_active)
        spine.set_linewidth(1.1)


def _set_button_enabled(
    button: Button,
    *,
    enabled: bool,
    palette: ManagedUiPalette,
) -> None:
    facecolor = palette.surface_facecolor if enabled else palette.surface_facecolor_disabled
    edgecolor = palette.surface_edgecolor_active if enabled else palette.surface_edgecolor_disabled
    text_color = palette.text_color if enabled else palette.disabled_text_color
    button.ax.set_facecolor(facecolor)
    button.color = facecolor
    button.hovercolor = palette.surface_hover_facecolor if enabled else facecolor
    button.label.set_color(text_color)
    for spine in button.ax.spines.values():
        spine.set_color(edgecolor)
        spine.set_linewidth(1.0)


def _sync_navigation_button_states(state: Managed2DPageWindowState) -> None:
    if state.ui_palette is None:
        return

    can_step_backward = state.start_page > 0
    can_step_forward = (state.start_page + state.visible_page_count) < state.total_pages

    if state.previous_page_button is not None:
        _set_button_enabled(
            state.previous_page_button,
            enabled=can_step_backward,
            palette=state.ui_palette,
        )
    if state.next_page_button is not None:
        _set_button_enabled(
            state.next_page_button,
            enabled=can_step_forward,
            palette=state.ui_palette,
        )


def _handle_page_submit(state: Managed2DPageWindowState, text: str) -> None:
    if state.is_syncing_inputs:
        return

    try:
        requested_page = int(text.strip())
    except ValueError:
        _sync_inputs(state)
        return

    _show_page_window(
        state,
        requested_page=requested_page,
        requested_visible_pages=state.visible_page_count,
    )


def _handle_visible_pages_submit(state: Managed2DPageWindowState, text: str) -> None:
    if state.is_syncing_inputs:
        return

    try:
        requested_visible_pages = int(text.strip())
    except ValueError:
        _sync_inputs(state)
        return

    _show_page_window(
        state,
        requested_page=state.start_page + 1,
        requested_visible_pages=requested_visible_pages,
    )


def _step_page(state: Managed2DPageWindowState, *, delta: int) -> None:
    _show_page_window(
        state,
        requested_page=(state.start_page + 1) + delta,
        requested_visible_pages=state.visible_page_count,
    )


def _step_visible_pages(state: Managed2DPageWindowState, *, delta: int) -> None:
    _show_page_window(
        state,
        requested_page=state.start_page + 1,
        requested_visible_pages=state.visible_page_count + delta,
    )


def _show_page_window(
    state: Managed2DPageWindowState,
    *,
    requested_page: int,
    requested_visible_pages: int,
) -> None:
    state.start_page = _clamp_page_index(requested_page, state.total_pages)
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
    _sync_navigation_button_states(state)


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
    hover_targets: list[_HoverTarget2D] = []

    for window_index, page_index in enumerate(_visible_page_indexes(state)):
        cache_entry = _cache_entry_for_page(state, page_index)
        window_page = _window_page(state, page_index=page_index, window_index=window_index)
        state.renderer._draw_page(
            state.axes,
            window_scene,
            window_page,
            cache_entry.projected_page,
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
    from .drawing import configure_zoom_text_scaling

    configure_zoom_text_scaling(state.axes, scene=window_scene)
    set_viewport_width(state.figure, viewport_width=window_scene.width)
    trim_gate_text_fit_cache(state.text_fit_cache)
    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


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


def _cache_entry_for_page(
    state: Managed2DPageWindowState,
    page_index: int,
) -> _PageWindowCacheEntry:
    cached_entry = state.page_cache.get(page_index)
    if cached_entry is not None:
        return cached_entry

    cache_entry = _PageWindowCacheEntry(projected_page=_project_page(state.scene, page_index))
    state.page_cache[page_index] = cache_entry
    return cache_entry


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
