"""Managed fixed-page-window helpers for 3D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.figure import Figure

from ..ir.lowering import lower_semantic_circuit
from ..ir.semantic import semantic_operation_id
from ..layout._layering import normalized_draw_circuit
from ..layout.topology_3d import TopologyName
from ..renderers._matplotlib_figure import clicked_artist_operation_id
from .exploration_2d import (
    Managed2DExplorationState,
    apply_scene_visual_state_3d,
    managed_exploration_state,
    next_selected_operation_id_for_block_action,
    reset_exploration_state,
    selected_block_action,
    toggle_wire_filter_mode,
    transform_semantic_circuit,
)
from .interaction import (
    is_block_toggle_key,
    is_clear_selection_key,
    is_end_key,
    is_home_key,
    is_minus_key,
    is_next_selection_key,
    is_page_down_key,
    is_page_up_key,
    is_plus_key,
    is_previous_selection_key,
    is_reset_view_key,
    is_shortcut_help_key,
    managed_key_name,
    managed_text_boxes_capture_keys,
    next_visible_operation_selection,
    toggle_operation_with_selection,
    visible_column_operation_ids,
)
from .page_window_3d_controls import (
    _attach_controls,
    _clamp_visible_page_count,
    _sync_inputs,
)
from .page_window_3d_ranges import (
    _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO,
    _projected_scene_aspect_ratio,
    windowed_3d_page_ranges,
    windowed_3d_page_scenes,
)
from .page_window_3d_render import _render_current_window
from .shortcut_help import create_shortcut_help_text, toggle_shortcut_help_text
from .ui_palette import ManagedUiPalette, managed_ui_palette
from .viewport import _figure_size_inches

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import Button, TextBox
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ..drawing.pipeline import PreparedDrawPipeline
    from ..layout.scene_3d import LayoutScene3D

__all__ = [
    "_MIN_3D_PAGE_PROJECTED_ASPECT_RATIO",
    "_projected_scene_aspect_ratio",
    "Managed3DPageWindowState",
    "configure_3d_page_window",
    "windowed_3d_page_ranges",
    "windowed_3d_page_scenes",
]


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
    wire_filter_button: Button | None = None
    ancilla_toggle_button: Button | None = None
    block_toggle_button: Button | None = None
    previous_page_button_axes: Axes | None = None
    page_axes: Axes | None = None
    next_page_button_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
    visible_pages_decrement_axes: Axes | None = None
    visible_pages_increment_axes: Axes | None = None
    wire_filter_axes: Axes | None = None
    ancilla_toggle_axes: Axes | None = None
    block_toggle_axes: Axes | None = None
    page_suffix_text: Text | None = None
    visible_suffix_text: Text | None = None
    shortcut_help_text: Text | None = None
    ui_palette: ManagedUiPalette | None = None
    is_syncing_inputs: bool = False
    exploration: Managed2DExplorationState | None = None
    keyboard_shortcuts_enabled: bool = True
    double_click_toggle_enabled: bool = True
    click_press_callback_id: int | None = None
    click_release_callback_id: int | None = None
    key_callback_id: int | None = None
    pending_click: tuple[float, float, Axes3D, bool] | None = None

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
        self.page_scenes = _styled_3d_page_scenes(
            updated_page_scenes,
            exploration=self.exploration,
        )
        self.total_pages = len(self.page_scenes)
        self.start_page = min(self.start_page, self.total_pages - 1)
        self.visible_page_count = _clamp_visible_page_count(
            self.visible_page_count,
            total_pages=self.total_pages,
            start_page=self.start_page,
        )
        _render_current_window(self)
        _sync_inputs(self)

    def select_operation(self, operation_id: str | None) -> None:
        """Update the contextual selection and redraw the current window."""

        if self.exploration is None:
            return
        self.exploration.selected_operation_id = operation_id
        _restyle_3d_page_window_scenes(self)
        _render_current_window(self)
        _sync_inputs(self)

    def toggle_wire_filter(self) -> None:
        """Toggle between all wires and only active wires."""

        if self.exploration is None:
            return
        self.exploration.wire_filter_mode = toggle_wire_filter_mode(
            self.exploration.wire_filter_mode
        )
        _refresh_3d_page_window_exploration_context(self)
        _render_current_window(self)
        _sync_inputs(self)

    def toggle_ancillas(self) -> None:
        """Toggle whether ancilla-like quantum wires remain visible."""

        if self.exploration is None:
            return
        self.exploration.show_ancillas = not self.exploration.show_ancillas
        _refresh_3d_page_window_exploration_context(self)
        _render_current_window(self)
        _sync_inputs(self)

    def toggle_selected_block(self) -> None:
        """Expand or collapse the semantic block that owns the selection."""

        if self.exploration is None:
            return
        block_action = selected_block_action(
            self.exploration.catalog,
            selected_operation_id=self.exploration.selected_operation_id,
            collapsed_block_ids=self.exploration.collapsed_block_ids,
        )
        if block_action is None:
            return
        if block_action.action == "expand":
            self.exploration.collapsed_block_ids.discard(block_action.block_id)
        else:
            self.exploration.collapsed_block_ids.add(block_action.block_id)
        self.exploration.selected_operation_id = next_selected_operation_id_for_block_action(
            self.exploration.catalog,
            block_action,
        )
        _refresh_3d_page_window_exploration_context(self)
        _render_current_window(self)
        _sync_inputs(self)

    def clear_selection(self) -> None:
        """Clear the current contextual selection."""

        self.select_operation(None)

    def reset_exploration_view(self) -> None:
        """Restore the managed exploration state to its original defaults."""

        if self.exploration is None:
            return
        reset_exploration_state(self.exploration)
        _refresh_3d_page_window_exploration_context(self)
        _render_current_window(self)
        _sync_inputs(self)

    def toggle_shortcut_help(self) -> None:
        """Toggle the managed shortcut-help overlay."""

        toggle_shortcut_help_text(self.shortcut_help_text, figure=self.figure)

    def step_page(self, delta: int) -> None:
        """Move the visible page window backward or forward."""

        self.start_page = min(max(0, self.start_page + delta), self.total_pages - 1)
        self.visible_page_count = _clamp_visible_page_count(
            self.visible_page_count,
            total_pages=self.total_pages,
            start_page=self.start_page,
        )
        _render_current_window(self)
        _sync_inputs(self)

    def step_visible_pages(self, delta: int) -> None:
        """Grow or shrink the visible page count."""

        self.visible_page_count = _clamp_visible_page_count(
            self.visible_page_count + delta,
            total_pages=self.total_pages,
            start_page=self.start_page,
        )
        _render_current_window(self)
        _sync_inputs(self)

    def show_first_page(self) -> None:
        """Jump to the absolute beginning of the paged window."""

        self.start_page = 0
        _render_current_window(self)
        _sync_inputs(self)

    def show_last_page(self) -> None:
        """Jump to the absolute end of the paged window."""

        self.start_page = max(0, self.total_pages - 1)
        self.visible_page_count = _clamp_visible_page_count(
            self.visible_page_count,
            total_pages=self.total_pages,
            start_page=self.start_page,
        )
        _render_current_window(self)
        _sync_inputs(self)

    def step_page_large(self, delta: int) -> None:
        """Move the visible page window by a large managed step."""

        self.step_page(delta * max(1, self.visible_page_count))

    def step_operation_selection(self, *, backwards: bool = False) -> None:
        """Move the selection across visible operations and advance pages when needed."""

        if self.exploration is None:
            return
        operation_ids = visible_column_operation_ids(
            gate
            for page_index in range(self.start_page, self.start_page + self.visible_page_count)
            for gate in self.page_scenes[page_index].gates
        )
        next_operation_id = next_visible_operation_selection(
            operation_ids,
            self.exploration.selected_operation_id,
            backwards=backwards,
            wrap=False,
        )
        if next_operation_id is not None:
            self.select_operation(next_operation_id)
            return
        if backwards:
            if self.start_page <= 0:
                return
            self.start_page -= 1
        else:
            if (self.start_page + self.visible_page_count) >= self.total_pages:
                return
            self.start_page += 1
        self.visible_page_count = _clamp_visible_page_count(
            self.visible_page_count,
            total_pages=self.total_pages,
            start_page=self.start_page,
        )
        _render_current_window(self)
        _sync_inputs(self)
        shifted_operation_ids = visible_column_operation_ids(
            gate
            for page_index in range(self.start_page, self.start_page + self.visible_page_count)
            for gate in self.page_scenes[page_index].gates
        )
        boundary_operation_id = (
            shifted_operation_ids[-1] if backwards and shifted_operation_ids else None
        ) or (shifted_operation_ids[0] if shifted_operation_ids else None)
        if boundary_operation_id is not None:
            self.select_operation(boundary_operation_id)

    def managed_text_boxes(self) -> tuple[object | None, ...]:
        """Return the managed text inputs that can capture keyboard input."""

        return (self.page_box, self.visible_pages_box)


def configure_3d_page_window(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    page_scenes: tuple[LayoutScene3D, ...],
    set_page_window: Callable[[Figure, object], None],
    keyboard_shortcuts_enabled: bool = True,
    double_click_toggle_enabled: bool = True,
) -> Managed3DPageWindowState:
    """Attach fixed page-window controls and render the initial 3D window."""

    normalized_pipeline = replace(
        pipeline,
        ir=normalized_draw_circuit(lower_semantic_circuit(pipeline.semantic_ir)),
    )
    base_axes = cast("Axes3D", axes)
    resolved_page_scenes = windowed_3d_page_scenes(
        normalized_pipeline,
        figure_size=_figure_size_inches(figure),
    )
    total_pages = max(1, len(resolved_page_scenes))
    ui_palette = managed_ui_palette(resolved_page_scenes[0].style.theme)
    exploration = managed_exploration_state(
        normalized_pipeline.semantic_ir,
        normalized_pipeline.expanded_semantic_ir,
    )
    exploration.transformed_semantic_ir = normalized_pipeline.semantic_ir
    state = Managed3DPageWindowState(
        figure=figure,
        base_axes=base_axes,
        pipeline=normalized_pipeline,
        page_scenes=_styled_3d_page_scenes(resolved_page_scenes, exploration=exploration),
        total_pages=total_pages,
        start_page=0,
        visible_page_count=1,
        ui_palette=ui_palette,
        exploration=exploration,
        keyboard_shortcuts_enabled=keyboard_shortcuts_enabled,
        double_click_toggle_enabled=double_click_toggle_enabled,
    )
    set_page_window(figure, state)
    _attach_controls(state)
    state.shortcut_help_text = create_shortcut_help_text(
        figure,
        palette=ui_palette,
        lines=(
            "Navigation",
            "Left/Right: Move pages",
            "Up/Down: Show more/fewer pages",
            "Home/End: Jump to first/last page",
            "PageUp/PageDown: Jump by visible window",
            "+/-: Show more/fewer pages",
            "",
            "Selection",
            "Tab/Shift+Tab: Move between columns",
            "Enter/Space: Toggle block",
            "Esc: Clear selection",
            "0: Reset exploration",
            "?: Show/hide this help",
        ),
    )
    _attach_3d_window_selection_clicks(state)
    _attach_3d_window_key_shortcuts(state)
    _render_current_window(state)
    _sync_inputs(state)
    return state


def _refresh_3d_page_window_exploration_context(state: Managed3DPageWindowState) -> None:
    if state.exploration is None:
        return

    transformed = transform_semantic_circuit(
        state.exploration.catalog,
        collapsed_block_ids=state.exploration.collapsed_block_ids,
        wire_filter_mode=state.exploration.wire_filter_mode,
        show_ancillas=state.exploration.show_ancillas,
    )
    transformed_operation_ids = {
        semantic_operation_id(operation)
        for layer in transformed.semantic_ir.layers
        for operation in layer.operations
    }
    if state.exploration.selected_operation_id not in transformed_operation_ids:
        state.exploration.selected_operation_id = None
    state.exploration.transformed_semantic_ir = transformed.semantic_ir

    normalized_circuit = normalized_draw_circuit(lower_semantic_circuit(transformed.semantic_ir))
    state.pipeline = replace(state.pipeline, ir=normalized_circuit)
    state.page_scenes = _styled_3d_page_scenes(
        windowed_3d_page_scenes(
            state.pipeline,
            figure_size=_figure_size_inches(state.figure),
        ),
        exploration=state.exploration,
    )
    state.total_pages = max(1, len(state.page_scenes))
    state.start_page = min(state.start_page, state.total_pages - 1)
    state.visible_page_count = _clamp_visible_page_count(
        state.visible_page_count,
        total_pages=state.total_pages,
        start_page=state.start_page,
    )


def _restyle_3d_page_window_scenes(state: Managed3DPageWindowState) -> None:
    state.page_scenes = _styled_3d_page_scenes(
        state.page_scenes,
        exploration=state.exploration,
    )


def _styled_3d_page_scenes(
    page_scenes: tuple[LayoutScene3D, ...],
    *,
    exploration: Managed2DExplorationState | None,
) -> tuple[LayoutScene3D, ...]:
    if exploration is None or exploration.transformed_semantic_ir is None:
        return page_scenes
    return tuple(
        apply_scene_visual_state_3d(
            scene,
            exploration.transformed_semantic_ir,
            selected_operation_id=exploration.selected_operation_id,
        )
        for scene in page_scenes
    )


def _attach_3d_window_selection_clicks(state: Managed3DPageWindowState) -> None:
    canvas = getattr(state.figure, "canvas", None)
    if canvas is None:
        return
    if state.click_press_callback_id is not None:
        canvas.mpl_disconnect(state.click_press_callback_id)
    if state.click_release_callback_id is not None:
        canvas.mpl_disconnect(state.click_release_callback_id)

    def _handle_press(event: MouseEvent) -> None:
        if state.exploration is None or event.inaxes not in state.display_axes or event.button != 1:
            state.pending_click = None
            return
        state.pending_click = (
            float(event.x),
            float(event.y),
            cast("Axes3D", event.inaxes),
            bool(event.dblclick),
        )

    def _handle_release(event: MouseEvent) -> None:
        if state.exploration is None:
            return
        pending_click = state.pending_click
        state.pending_click = None
        if pending_click is None or event.inaxes not in state.display_axes or event.button != 1:
            return
        clicked_axes = cast("Axes3D", event.inaxes)
        if clicked_axes is not pending_click[2]:
            return
        if (
            (float(event.x) - pending_click[0]) ** 2 + (float(event.y) - pending_click[1]) ** 2
        ) ** 0.5 > 6.0:
            return
        operation_id = clicked_artist_operation_id(clicked_axes, event)
        if state.double_click_toggle_enabled and pending_click[3]:
            toggle_operation_with_selection(state, operation_id)
            return
        state.select_operation(operation_id)

    state.click_press_callback_id = int(canvas.mpl_connect("button_press_event", _handle_press))
    state.click_release_callback_id = int(
        canvas.mpl_connect("button_release_event", _handle_release)
    )


def _attach_3d_window_key_shortcuts(state: Managed3DPageWindowState) -> None:
    canvas = getattr(state.figure, "canvas", None)
    if canvas is None:
        return
    if state.key_callback_id is not None:
        canvas.mpl_disconnect(state.key_callback_id)

    def _handle_key(event: KeyEvent) -> None:
        if not state.keyboard_shortcuts_enabled:
            return
        if managed_text_boxes_capture_keys(state.managed_text_boxes()):
            return
        key_name = managed_key_name(event)
        if is_home_key(event):
            state.show_first_page()
            return
        if is_end_key(event):
            state.show_last_page()
            return
        if is_page_up_key(event):
            state.step_page_large(-1)
            return
        if is_page_down_key(event):
            state.step_page_large(1)
            return
        if is_plus_key(event):
            state.step_visible_pages(1)
            return
        if is_minus_key(event):
            state.step_visible_pages(-1)
            return
        if is_next_selection_key(event):
            state.step_operation_selection()
            return
        if is_previous_selection_key(event):
            state.step_operation_selection(backwards=True)
            return
        if is_clear_selection_key(event):
            state.clear_selection()
            return
        if is_reset_view_key(event):
            state.reset_exploration_view()
            return
        if is_shortcut_help_key(event):
            state.toggle_shortcut_help()
            return
        if key_name == "left":
            state.step_page(-1)
            return
        if key_name == "right":
            state.step_page(1)
            return
        if key_name == "up":
            state.step_visible_pages(1)
            return
        if key_name == "down":
            state.step_visible_pages(-1)
            return
        if is_block_toggle_key(event):
            state.toggle_selected_block()

    state.key_callback_id = int(canvas.mpl_connect("key_press_event", _handle_key))
