"""Managed fixed-page-window helpers for 3D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from ._draw_managed_slider import (
    _style_control_axes,
    _style_text_box,
    circuit_window,
    page_slider_window_size,
)
from ._draw_pipeline import _compute_3d_scene
from ._managed_3d_view_state import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    Managed3DFixedViewState,
    capture_managed_3d_view_state,
)
from ._managed_ui_palette import ManagedUiPalette, managed_ui_palette
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

_DISPLAY_AREA_LEFT = 0.02
_DISPLAY_AREA_BOTTOM = 0.18
_DISPLAY_AREA_WIDTH = 0.96
_DISPLAY_AREA_HEIGHT = 0.8
_DISPLAY_AXES_VERTICAL_GAP = 0.02
_PREVIOUS_PAGE_BUTTON_BOUNDS = (0.132, 0.05, 0.048, 0.06)
_PAGE_BOX_BOUNDS = (0.188, 0.05, 0.078, 0.06)
_NEXT_PAGE_BUTTON_BOUNDS = (0.274, 0.05, 0.048, 0.06)
_VISIBLE_PAGES_BOX_BOUNDS = (0.505, 0.05, 0.078, 0.06)
_PAGE_LABEL_POSITION = (0.075, 0.079)
_PAGE_SUFFIX_POSITION = (0.33, 0.079)
_VISIBLE_LABEL_POSITION = (0.392, 0.079)
_VISIBLE_SUFFIX_POSITION = (0.628, 0.079)


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
    previous_page_button: Button | None = None
    next_page_button: Button | None = None
    previous_page_button_axes: Axes | None = None
    page_axes: Axes | None = None
    next_page_button_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
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
        self.pipeline = replace(self.pipeline, draw_options=updated_draw_options)
        self.page_scenes = _page_scenes_for_pipeline(self.pipeline)
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

    state.previous_page_button = previous_page_button
    state.page_box = page_box
    state.next_page_button = next_page_button
    state.visible_pages_box = visible_pages_box
    state.previous_page_button_axes = previous_page_button_axes
    state.page_axes = page_axes
    state.next_page_button_axes = next_page_button_axes
    state.visible_pages_axes = visible_pages_axes
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
        axes.remove()

    display_axes = tuple(current_axes[: state.visible_page_count])
    for axes, bounds in zip(display_axes, target_bounds, strict=True):
        axes.set_position(bounds)
        setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, bounds)
        if fixed_view_state is not None:
            setattr(axes, _MANAGED_3D_FIXED_VIEW_STATE_ATTR, fixed_view_state)

    state.display_axes = display_axes
    return display_axes


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


def _page_scenes_for_pipeline(pipeline: PreparedDrawPipeline) -> tuple[LayoutScene3D, ...]:
    total_columns = len(pipeline.ir.layers)
    window_size = page_slider_window_size(pipeline.ir, pipeline.normalized_style)
    start_columns = (0,) if total_columns == 0 else tuple(range(0, total_columns, window_size))
    return tuple(
        _compute_3d_scene(
            cast("LayoutEngine3DLike", pipeline.layout_engine),
            circuit_window(
                pipeline.ir,
                start_column=start_column,
                window_size=window_size,
            ),
            pipeline.normalized_style,
            topology_name=pipeline.draw_options.topology,
            direct=pipeline.draw_options.direct,
            hover_enabled=pipeline.draw_options.hover.enabled,
        )
        for start_column in start_columns
    )
