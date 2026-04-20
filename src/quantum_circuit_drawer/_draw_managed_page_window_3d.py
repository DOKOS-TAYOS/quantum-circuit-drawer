"""Managed fixed-page-window helpers for 3D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ._draw_managed_slider import (
    _style_control_axes,
    _style_stepper_button,
    _style_text_box,
    circuit_window,
)
from ._draw_pipeline import _compute_3d_scene
from ._managed_3d_view_state import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    Managed3DFixedViewState,
    capture_managed_3d_view_state,
)
from ._managed_ui_palette import ManagedUiPalette, managed_ui_palette
from .ir.circuit import CircuitIR
from .layout._layering import normalized_draw_circuit
from .layout.topology_3d import TopologyName
from .renderers._matplotlib_figure import clear_hover_state
from .renderers.matplotlib_renderer_3d import _MANAGED_3D_VIEWPORT_BOUNDS_ATTR
from .typing import LayoutEngine3DLike

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import Button, TextBox
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ._draw_pipeline import PreparedDrawPipeline
    from .layout.scene_3d import LayoutScene3D
    from .renderers.matplotlib_renderer_3d import MatplotlibRenderer3D

_DISPLAY_AREA_LEFT = 0.02
_DISPLAY_AREA_BOTTOM = 0.18
_DISPLAY_AREA_WIDTH = 0.96
_DISPLAY_AREA_HEIGHT = 0.8
_DISPLAY_AXES_VERTICAL_GAP = 0.02
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
_MIN_3D_PAGE_PROJECTED_ASPECT_RATIO = 1.2


@dataclass(slots=True)
class Managed3DPageWindowState:
    """Managed fixed-page-window state attached to one 3D figure."""

    figure: Figure
    base_axes: Axes3D
    pipeline: PreparedDrawPipeline
    page_scenes: tuple[LayoutScene3D, ...]
    total_pages: int
    start_page: int
    visible_page_count: int
    display_axes: tuple[Axes3D, ...] = ()
    page_box: TextBox | None = None
    visible_pages_box: TextBox | None = None
    visible_pages_decrement_button: Button | None = None
    visible_pages_increment_button: Button | None = None
    previous_page_button: Button | None = None
    next_page_button: Button | None = None
    previous_page_button_axes: Axes | None = None
    page_axes: Axes | None = None
    next_page_button_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
    visible_pages_decrement_axes: Axes | None = None
    visible_pages_increment_axes: Axes | None = None
    page_suffix_text: Text | None = None
    visible_suffix_text: Text | None = None
    ui_palette: ManagedUiPalette | None = None
    is_syncing_inputs: bool = False

    @property
    def current_scene(self) -> LayoutScene3D:
        """Return the first scene currently shown in the window."""

        return self.page_scenes[self.start_page]

    def select_topology(self, topology: TopologyName) -> None:
        """Switch topology while preserving the current window state."""

        updated_draw_options = replace(self.pipeline.draw_options, topology=topology)
        updated_pipeline = replace(self.pipeline, draw_options=updated_draw_options)
        updated_page_scenes = windowed_3d_page_scenes(
            updated_pipeline,
            figure_size=_figure_size_inches(self.figure),
        )
        self.pipeline = replace(updated_pipeline, paged_scene=updated_page_scenes[0])
        self.page_scenes = updated_page_scenes
        self.total_pages = len(self.page_scenes)
        self.start_page = min(self.start_page, self.total_pages - 1)
        self.visible_page_count = _clamp_visible_page_count(
            self.visible_page_count,
            total_pages=self.total_pages,
            start_page=self.start_page,
        )
        _render_current_window(self)
        _sync_inputs(self)


def configure_3d_page_window(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    page_scenes: tuple[LayoutScene3D, ...],
    set_page_window: Callable[[Figure, object], None],
) -> Managed3DPageWindowState:
    """Attach fixed page-window controls and render the initial 3D window."""

    base_axes = cast("Axes3D", axes)
    total_pages = max(1, len(page_scenes))
    ui_palette = managed_ui_palette(page_scenes[0].style.theme)
    state = Managed3DPageWindowState(
        figure=figure,
        base_axes=base_axes,
        pipeline=pipeline,
        page_scenes=page_scenes,
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


def _attach_controls(state: Managed3DPageWindowState) -> None:
    from matplotlib.widgets import Button, TextBox

    palette = state.ui_palette or managed_ui_palette(state.current_scene.style.theme)

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

    state.previous_page_button = previous_page_button
    state.page_box = page_box
    state.next_page_button = next_page_button
    state.visible_pages_box = visible_pages_box
    state.visible_pages_decrement_button = visible_pages_decrement_button
    state.visible_pages_increment_button = visible_pages_increment_button
    state.previous_page_button_axes = previous_page_button_axes
    state.page_axes = page_axes
    state.next_page_button_axes = next_page_button_axes
    state.visible_pages_axes = visible_pages_axes
    state.visible_pages_decrement_axes = visible_pages_decrement_axes
    state.visible_pages_increment_axes = visible_pages_increment_axes
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


def _sync_navigation_button_states(state: Managed3DPageWindowState) -> None:
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


def _handle_page_submit(state: Managed3DPageWindowState, text: str) -> None:
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


def _handle_visible_pages_submit(state: Managed3DPageWindowState, text: str) -> None:
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


def _step_page(state: Managed3DPageWindowState, *, delta: int) -> None:
    _show_page_window(
        state,
        requested_page=(state.start_page + 1) + delta,
        requested_visible_pages=state.visible_page_count,
    )


def _step_visible_pages(state: Managed3DPageWindowState, *, delta: int) -> None:
    _show_page_window(
        state,
        requested_page=state.start_page + 1,
        requested_visible_pages=state.visible_page_count + delta,
    )


def _show_page_window(
    state: Managed3DPageWindowState,
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


def _sync_inputs(state: Managed3DPageWindowState) -> None:
    if state.page_box is None or state.visible_pages_box is None:
        return

    state.is_syncing_inputs = True
    try:
        state.page_box.set_val(str(state.start_page + 1))
        state.visible_pages_box.set_val(str(state.visible_page_count))
    finally:
        state.is_syncing_inputs = False
    _sync_total_page_texts(state)
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


def _render_current_window(state: Managed3DPageWindowState) -> None:
    state.figure.patch.set_facecolor(state.current_scene.style.theme.figure_facecolor)
    fixed_view_state = _capture_shared_view_state(state)
    display_axes = _ensure_display_axes(
        state,
        fixed_view_state=fixed_view_state,
    )
    for axes, page_scene in zip(display_axes, _visible_page_scenes(state), strict=True):
        clear_hover_state(axes)
        axes.clear()
        bounds = cast(
            "tuple[float, float, float, float]",
            getattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR),
        )
        axes.set_position(bounds)
        if fixed_view_state is not None:
            setattr(axes, _MANAGED_3D_FIXED_VIEW_STATE_ATTR, fixed_view_state)
        state.pipeline.renderer.render(page_scene, ax=axes)

    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _capture_shared_view_state(
    state: Managed3DPageWindowState,
) -> Managed3DFixedViewState | None:
    if not state.display_axes:
        return None
    return capture_managed_3d_view_state(state.display_axes[0])


def _ensure_display_axes(
    state: Managed3DPageWindowState,
    *,
    fixed_view_state: Managed3DFixedViewState | None,
) -> tuple[Axes3D, ...]:
    target_bounds = _display_axes_bounds(state.visible_page_count)
    current_axes = list(state.display_axes or (state.base_axes,))

    while len(current_axes) < state.visible_page_count:
        current_axes.append(
            cast(
                "Axes3D",
                state.figure.add_axes((0.0, 0.0, 1.0, 1.0), projection="3d"),
            )
        )

    for axes in current_axes[state.visible_page_count :]:
        clear_hover_state(axes)
        _disconnect_removed_3d_axes_callbacks(axes)
        axes.remove()

    display_axes = tuple(current_axes[: state.visible_page_count])
    for axes, bounds in zip(display_axes, target_bounds, strict=True):
        axes.set_position(bounds)
        setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, bounds)
        if fixed_view_state is not None:
            setattr(axes, _MANAGED_3D_FIXED_VIEW_STATE_ATTR, fixed_view_state)

    state.display_axes = display_axes
    return display_axes


def _disconnect_removed_3d_axes_callbacks(axes: Axes3D) -> None:
    canvas = getattr(axes.figure, "canvas", None)
    callbacks = getattr(canvas, "callbacks", None)
    registry = getattr(callbacks, "callbacks", None)
    if canvas is None or callbacks is None or not isinstance(registry, dict):
        return

    for signal_name in ("motion_notify_event", "button_press_event", "button_release_event"):
        signal_callbacks = registry.get(signal_name, {})
        for callback_id, callback_proxy in tuple(signal_callbacks.items()):
            callback = callback_proxy()
            if callback is None:
                continue
            if getattr(callback, "__self__", None) is axes:
                callbacks.disconnect(callback_id)


def _visible_page_scenes(state: Managed3DPageWindowState) -> tuple[LayoutScene3D, ...]:
    end_page = state.start_page + state.visible_page_count
    return state.page_scenes[state.start_page : end_page]


def _display_axes_bounds(
    visible_page_count: int,
) -> tuple[tuple[float, float, float, float], ...]:
    if visible_page_count <= 1:
        return (
            (_DISPLAY_AREA_LEFT, _DISPLAY_AREA_BOTTOM, _DISPLAY_AREA_WIDTH, _DISPLAY_AREA_HEIGHT),
        )

    total_gap = _DISPLAY_AXES_VERTICAL_GAP * (visible_page_count - 1)
    axes_height = (_DISPLAY_AREA_HEIGHT - total_gap) / float(visible_page_count)
    bounds: list[tuple[float, float, float, float]] = []
    for window_index in range(visible_page_count):
        bottom = _DISPLAY_AREA_BOTTOM + (
            (visible_page_count - window_index - 1) * (axes_height + _DISPLAY_AXES_VERTICAL_GAP)
        )
        bounds.append((_DISPLAY_AREA_LEFT, bottom, _DISPLAY_AREA_WIDTH, axes_height))
    return tuple(bounds)


def windowed_3d_page_scenes(
    pipeline: PreparedDrawPipeline,
    *,
    figure_size: tuple[float, float] | None = None,
) -> tuple[LayoutScene3D, ...]:
    page_ranges = windowed_3d_page_ranges(pipeline, figure_size=figure_size)
    normalized_circuit = normalized_draw_circuit(pipeline.ir)
    return tuple(
        _compute_3d_scene(
            cast("LayoutEngine3DLike", pipeline.layout_engine),
            circuit_window(
                normalized_circuit,
                start_column=start_column,
                window_size=max(1, end_column - start_column + 1),
            ),
            pipeline.normalized_style,
            topology_name=pipeline.draw_options.topology,
            direct=pipeline.draw_options.direct,
            hover_enabled=pipeline.draw_options.hover.enabled,
        )
        for start_column, end_column in page_ranges
    )


def windowed_3d_page_ranges(
    pipeline: PreparedDrawPipeline,
    *,
    figure_size: tuple[float, float] | None = None,
    axes_bounds: tuple[float, float, float, float] | None = None,
) -> tuple[tuple[int, int], ...]:
    from ._draw_managed import page_window_adaptive_paged_scene
    from .layout._layering import normalized_draw_circuit
    from .layout.engine import LayoutEngine
    from .renderers._matplotlib_figure import create_managed_figure

    layout_engine_2d = LayoutEngine()
    initial_scene = layout_engine_2d.compute(pipeline.ir, pipeline.normalized_style)
    initial_scene.hover = pipeline.draw_options.hover
    figure_width, figure_height = figure_size or (
        max(4.6, initial_scene.width * 0.95),
        max(2.1, initial_scene.page_height * 0.72),
    )
    figure, axes = create_managed_figure(
        initial_scene,
        figure_width=figure_width,
        figure_height=figure_height,
        use_agg=True,
    )
    if axes_bounds is not None:
        axes.set_position(axes_bounds)
    try:
        adapted_scene, _ = page_window_adaptive_paged_scene(
            pipeline.ir,
            layout_engine_2d,
            pipeline.normalized_style,
            axes,
            hover_enabled=initial_scene.hover.enabled,
            initial_scene=initial_scene,
            visible_page_count=1,
        )
    finally:
        figure.clear()

    normalized_circuit = normalized_draw_circuit(pipeline.ir)
    page_ranges = tuple((page.start_column, page.end_column) for page in adapted_scene.pages) or (
        (0, max(0, len(normalized_circuit.layers) - 1)),
    )
    return _rebalance_narrow_3d_page_ranges(
        pipeline,
        normalized_circuit=normalized_circuit,
        page_ranges=page_ranges,
        figure_size=(figure_width, figure_height),
        axes_bounds=axes_bounds,
    )


def _rebalance_narrow_3d_page_ranges(
    pipeline: PreparedDrawPipeline,
    *,
    normalized_circuit: CircuitIR,
    page_ranges: tuple[tuple[int, int], ...],
    figure_size: tuple[float, float],
    axes_bounds: tuple[float, float, float, float] | None,
) -> tuple[tuple[int, int], ...]:
    if not page_ranges:
        return page_ranges

    first_start_column, first_end_column = page_ranges[0]
    first_window_size = max(1, first_end_column - first_start_column + 1)
    if first_window_size <= 1:
        return page_ranges

    aspect_ratio_cache: dict[int, float] = {}

    def projected_aspect_ratio(window_size: int) -> float:
        cached_ratio = aspect_ratio_cache.get(window_size)
        if cached_ratio is not None:
            return cached_ratio
        scene = _compute_3d_scene(
            cast("LayoutEngine3DLike", pipeline.layout_engine),
            circuit_window(
                normalized_circuit,
                start_column=0,
                window_size=window_size,
            ),
            pipeline.normalized_style,
            topology_name=pipeline.draw_options.topology,
            direct=pipeline.draw_options.direct,
            hover_enabled=pipeline.draw_options.hover.enabled,
        )
        cached_ratio = _projected_scene_aspect_ratio(
            scene=scene,
            renderer=cast("MatplotlibRenderer3D", pipeline.renderer),
            figure_size=figure_size,
            axes_bounds=axes_bounds,
        )
        aspect_ratio_cache[window_size] = cached_ratio
        return cached_ratio

    if projected_aspect_ratio(first_window_size) >= _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO:
        return page_ranges

    low = 1
    high = first_window_size
    best_window_size = 1
    while low <= high:
        middle = (low + high) // 2
        if projected_aspect_ratio(middle) >= _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO:
            best_window_size = middle
            low = middle + 1
        else:
            high = middle - 1

    if best_window_size >= first_window_size:
        return page_ranges
    return _uniform_3d_page_ranges(
        total_columns=len(normalized_circuit.layers),
        window_size=best_window_size,
    )


def _uniform_3d_page_ranges(
    *,
    total_columns: int,
    window_size: int,
) -> tuple[tuple[int, int], ...]:
    if total_columns <= 0:
        return ((0, 0),)

    ranges: list[tuple[int, int]] = []
    start_column = 0
    resolved_window_size = max(1, window_size)
    while start_column < total_columns:
        end_column = min(total_columns - 1, start_column + resolved_window_size - 1)
        ranges.append((start_column, end_column))
        start_column = end_column + 1
    return tuple(ranges)


def _projected_scene_aspect_ratio(
    *,
    scene: LayoutScene3D,
    renderer: MatplotlibRenderer3D,
    figure_size: tuple[float, float],
    axes_bounds: tuple[float, float, float, float] | None = None,
) -> float:
    from .renderers._matplotlib_figure import create_managed_figure

    figure, axes = create_managed_figure(
        scene,
        figure_width=figure_size[0],
        figure_height=figure_size[1],
        use_agg=True,
        projection="3d",
    )
    resolved_axes_bounds = axes_bounds or _display_axes_bounds(1)[0]
    axes_3d = cast("Axes3D", axes)
    axes_3d.set_position(resolved_axes_bounds)
    setattr(axes_3d, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, resolved_axes_bounds)
    try:
        renderer._prepare_axes(axes_3d, scene)
        renderer._expand_axes_to_fill_viewport(axes_3d, resolved_axes_bounds)
        renderer._synchronize_axes_geometry(axes_3d)
        render_context = renderer._create_render_context(axes_3d)
        projected_points = renderer._projected_scene_geometry_points(
            axes_3d,
            scene,
            render_context=render_context,
        )
        if projected_points.size == 0:
            return float("inf")

        x_values = tuple(float(value) for value in projected_points[:, 0])
        y_values = tuple(float(value) for value in projected_points[:, 1])
        projected_width = max(x_values) - min(x_values)
        projected_height = max(y_values) - min(y_values)
        if projected_height <= 0.0:
            return float("inf")
        return projected_width / projected_height
    finally:
        figure.clear()


def _sync_total_page_texts(state: Managed3DPageWindowState) -> None:
    total_pages_text = f"/ {state.total_pages}"
    if state.page_suffix_text is not None:
        state.page_suffix_text.set_text(total_pages_text)
    if state.visible_suffix_text is not None:
        state.visible_suffix_text.set_text(total_pages_text)


def _figure_size_inches(figure: Figure) -> tuple[float, float]:
    size_inches = figure.get_size_inches()
    return float(size_inches[0]), float(size_inches[1])
