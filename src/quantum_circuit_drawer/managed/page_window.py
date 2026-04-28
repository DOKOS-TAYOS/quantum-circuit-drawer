"""Managed fixed-page-window facade for 2D rendering."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.figure import Figure

from ..ir.lowering import lower_semantic_circuit, semantic_circuit_from_circuit_ir
from ..ir.semantic import semantic_operation_id
from ..layout._layering import normalized_draw_circuit
from ..layout.scene import LayoutScene
from ..renderers._matplotlib_page_projection import _ProjectedPage
from ..renderers.matplotlib_primitives import _GateTextCache
from ..renderers.matplotlib_renderer import MatplotlibRenderer
from ..style import DrawStyle
from ..style.defaults import replace_draw_style
from ..typing import LayoutEngineLike
from .exploration_2d import (
    Managed2DExplorationState,
    append_wire_fold_markers,
    apply_scene_visual_state,
    clicked_operation_id,
    managed_exploration_state,
    next_selected_operation_id_for_block_action,
    reset_exploration_state,
    selected_block_action,
    toggle_wire_filter_mode,
    transform_semantic_circuit,
)
from .interaction import (
    install_managed_tab_focus_bindings,
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
    is_toggle_wire_filter_key,
    managed_key_name,
    managed_text_boxes_capture_keys,
    next_visible_operation_selection,
    run_managed_canvas_action,
    toggle_operation_with_selection,
    visible_column_operation_ids,
)
from .page_window_controls import _MAIN_AXES_BOUNDS, _attach_controls, _sync_inputs
from .page_window_render import _render_current_window
from .page_window_windowing import _clamp_page_index, _clamp_visible_page_count
from .shortcut_help import create_shortcut_help_text, toggle_shortcut_help_text
from .ui_palette import ManagedUiPalette, managed_ui_palette
from .viewport import compute_paged_scene

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import Button, TextBox

    from ..ir.circuit import CircuitIR
    from ..ir.semantic import SemanticCircuitIR


@dataclass(slots=True)
class Managed2DPageWindowState:
    """Managed fixed-page-window state attached to one figure."""

    figure: Figure
    axes: Axes
    circuit: CircuitIR
    layout_engine: LayoutEngineLike
    renderer: MatplotlibRenderer
    style: DrawStyle
    base_scene: LayoutScene
    scene: LayoutScene
    window_scene: LayoutScene | None
    effective_page_width: float
    total_pages: int
    start_page: int
    visible_page_count: int
    page_cache: dict[int, _ProjectedPage] = field(default_factory=dict)
    text_fit_cache: _GateTextCache = field(default_factory=dict)
    page_box: TextBox | None = None
    visible_pages_box: TextBox | None = None
    visible_pages_decrement_button: Button | None = None
    visible_pages_increment_button: Button | None = None
    previous_page_button: Button | None = None
    next_page_button: Button | None = None
    wire_filter_button: Button | None = None
    ancilla_toggle_button: Button | None = None
    block_toggle_button: Button | None = None
    page_axes: Axes | None = None
    visible_pages_axes: Axes | None = None
    visible_pages_decrement_axes: Axes | None = None
    visible_pages_increment_axes: Axes | None = None
    previous_page_button_axes: Axes | None = None
    next_page_button_axes: Axes | None = None
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
    click_callback_id: int | None = None
    key_callback_id: int | None = None

    def select_operation(self, operation_id: str | None) -> None:
        """Update the contextual selection and redraw the current page window."""

        if self.exploration is None:
            return
        self.exploration.selected_operation_id = operation_id
        _restyle_page_window_scene(self)
        _render_current_window(self)
        _sync_inputs(self)

    def toggle_wire_filter(self) -> None:
        """Toggle between all wires and only the currently active wires."""

        if self.exploration is None:
            return
        self.exploration.wire_filter_mode = toggle_wire_filter_mode(
            self.exploration.wire_filter_mode
        )
        _refresh_page_window_exploration_context(self)
        _render_current_window(self)
        _sync_inputs(self)

    def toggle_ancillas(self) -> None:
        """Toggle whether ancilla-like quantum wires remain visible."""

        if self.exploration is None:
            return
        self.exploration.show_ancillas = not self.exploration.show_ancillas
        _refresh_page_window_exploration_context(self)
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
        _refresh_page_window_exploration_context(self)
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
        _refresh_page_window_exploration_context(self)
        _render_current_window(self)
        _sync_inputs(self)

    def toggle_shortcut_help(self) -> None:
        """Toggle the managed shortcut-help overlay."""

        toggle_shortcut_help_text(self.shortcut_help_text, figure=self.figure)

    def step_page(self, delta: int) -> None:
        """Move the visible page window backward or forward."""

        self.start_page = _clamp_page_index((self.start_page + 1) + delta, self.total_pages)
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
            (
                *((self.window_scene or self.scene).gates),
                *((self.window_scene or self.scene).measurements),
            ),
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
            (
                *((self.window_scene or self.scene).gates),
                *((self.window_scene or self.scene).measurements),
            )
        )
        boundary_operation_id = (
            shifted_operation_ids[-1] if backwards and shifted_operation_ids else None
        ) or (shifted_operation_ids[0] if shifted_operation_ids else None)
        if boundary_operation_id is not None:
            self.select_operation(boundary_operation_id)

    def managed_text_boxes(self) -> tuple[object | None, ...]:
        """Return the managed text inputs that can capture keyboard input."""

        return (self.page_box, self.visible_pages_box)


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
    semantic_ir: SemanticCircuitIR | None = None,
    expanded_semantic_ir: SemanticCircuitIR | None = None,
    keyboard_shortcuts_enabled: bool = True,
    double_click_toggle_enabled: bool = True,
) -> Managed2DPageWindowState:
    """Attach fixed page-window controls and render the initial visible window."""

    ui_palette = managed_ui_palette(scene.style.theme)
    current_semantic = semantic_ir or semantic_circuit_from_circuit_ir(circuit)
    current_circuit = normalized_draw_circuit(lower_semantic_circuit(current_semantic))
    current_scene = compute_paged_scene(
        current_circuit,
        layout_engine,
        replace_draw_style(scene.style, max_page_width=effective_page_width),
        hover_enabled=scene.hover.enabled,
    )
    current_scene.hover = scene.hover
    total_pages = max(1, len(current_scene.pages))
    exploration = managed_exploration_state(
        current_semantic,
        expanded_semantic_ir or current_semantic,
    )
    exploration.transformed_semantic_ir = current_semantic

    state = Managed2DPageWindowState(
        figure=figure,
        axes=axes,
        circuit=current_circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        style=current_scene.style,
        base_scene=current_scene,
        scene=current_scene,
        window_scene=None,
        effective_page_width=effective_page_width,
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
            "w: Toggle wires all/active",
            "",
            "Selection",
            "Tab/Shift+Tab: Move between columns",
            "Enter/Space: Toggle block",
            "Esc: Clear selection",
            "0: Reset exploration",
            "?: Show/hide this help",
        ),
    )
    _attach_window_selection_clicks(state)
    _attach_window_key_shortcuts(state)
    _render_current_window(state)
    _sync_inputs(state)
    return state


def apply_page_window_axes_bounds(axes: Axes) -> None:
    """Pin page-window drawing axes above the control row."""

    axes.set_position(_MAIN_AXES_BOUNDS)


__all__ = [
    "Axes",
    "Callable",
    "Figure",
    "LayoutEngineLike",
    "LayoutScene",
    "Managed2DPageWindowState",
    "ManagedUiPalette",
    "MatplotlibRenderer",
    "TYPE_CHECKING",
    "_GateTextCache",
    "_MAIN_AXES_BOUNDS",
    "_ProjectedPage",
    "_attach_controls",
    "_render_current_window",
    "_sync_inputs",
    "annotations",
    "apply_page_window_axes_bounds",
    "configure_page_window",
    "dataclass",
    "field",
    "managed_ui_palette",
]


def _refresh_page_window_exploration_context(state: Managed2DPageWindowState) -> None:
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
    state.exploration.hidden_wire_ranges = transformed.hidden_wire_ranges

    normalized_circuit = normalized_draw_circuit(transformed.circuit_ir)
    state.circuit = normalized_circuit
    base_hover = state.base_scene.hover
    state.base_scene = compute_paged_scene(
        normalized_circuit,
        state.layout_engine,
        replace_draw_style(state.style, max_page_width=state.effective_page_width),
        hover_enabled=base_hover.enabled,
    )
    state.base_scene.hover = base_hover
    _restyle_page_window_scene(state)
    state.total_pages = max(1, len(state.scene.pages))
    state.start_page = _clamp_page_index(state.start_page + 1, state.total_pages)
    state.visible_page_count = _clamp_visible_page_count(
        state.visible_page_count,
        total_pages=state.total_pages,
        start_page=state.start_page,
    )
    state.window_scene = None


def _restyle_page_window_scene(state: Managed2DPageWindowState) -> None:
    if state.exploration is None or state.exploration.transformed_semantic_ir is None:
        state.scene = state.base_scene
    else:
        state.scene = append_wire_fold_markers(
            apply_scene_visual_state(
                state.base_scene,
                state.exploration.transformed_semantic_ir,
                selected_operation_id=state.exploration.selected_operation_id,
            ),
            state.exploration.hidden_wire_ranges,
        )
    state.page_cache.clear()


def _attach_window_selection_clicks(state: Managed2DPageWindowState) -> None:
    canvas = getattr(state.figure, "canvas", None)
    if canvas is None:
        return
    if state.click_callback_id is not None:
        canvas.mpl_disconnect(state.click_callback_id)

    def _handle_click(event: MouseEvent) -> None:
        if state.exploration is None:
            return
        if event.inaxes is not state.axes:
            return
        click_scene = state.window_scene or state.scene
        operation_id = clicked_operation_id(state.axes, click_scene, event)
        if state.double_click_toggle_enabled and event.dblclick:
            toggle_operation_with_selection(state, operation_id)
            return
        state.select_operation(operation_id)

    state.click_callback_id = int(canvas.mpl_connect("button_press_event", _handle_click))


def _attach_window_key_shortcuts(state: Managed2DPageWindowState) -> None:
    canvas = getattr(state.figure, "canvas", None)
    if canvas is None:
        return
    if state.key_callback_id is not None:
        canvas.mpl_disconnect(state.key_callback_id)
    install_managed_tab_focus_bindings(canvas)

    def _handle_key(event: KeyEvent) -> None:
        if not state.keyboard_shortcuts_enabled:
            return
        if managed_text_boxes_capture_keys(state.managed_text_boxes()):
            return

        def _run(action: Callable[[], None]) -> None:
            run_managed_canvas_action(canvas, action)

        key_name = managed_key_name(event)
        if is_home_key(event):
            _run(state.show_first_page)
            return
        if is_end_key(event):
            _run(state.show_last_page)
            return
        if is_page_up_key(event):
            _run(lambda: state.step_page_large(-1))
            return
        if is_page_down_key(event):
            _run(lambda: state.step_page_large(1))
            return
        if is_plus_key(event):
            _run(lambda: state.step_visible_pages(1))
            return
        if is_minus_key(event):
            _run(lambda: state.step_visible_pages(-1))
            return
        if is_next_selection_key(event):
            _run(state.step_operation_selection)
            return
        if is_previous_selection_key(event):
            _run(lambda: state.step_operation_selection(backwards=True))
            return
        if is_clear_selection_key(event):
            _run(state.clear_selection)
            return
        if is_reset_view_key(event):
            _run(state.reset_exploration_view)
            return
        if is_toggle_wire_filter_key(event):
            _run(state.toggle_wire_filter)
            return
        if is_shortcut_help_key(event):
            _run(state.toggle_shortcut_help)
            return
        if key_name == "left":
            _run(lambda: state.step_page(-1))
            return
        if key_name == "right":
            _run(lambda: state.step_page(1))
            return
        if key_name == "up":
            _run(lambda: state.step_visible_pages(1))
            return
        if key_name == "down":
            _run(lambda: state.step_visible_pages(-1))
            return
        if is_block_toggle_key(event):
            _run(state.toggle_selected_block)

    state.key_callback_id = int(canvas.mpl_connect("key_press_event", _handle_key))
