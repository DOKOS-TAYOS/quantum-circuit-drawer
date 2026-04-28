"""Managed 2D slider helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.figure import Figure

from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit, semantic_circuit_from_circuit_ir
from ..ir.semantic import semantic_operation_id
from ..layout._layering import normalized_draw_circuit
from ..layout.scene import LayoutScene
from ..renderers._matplotlib_figure import clear_hover_state, set_viewport_width
from ..renderers.matplotlib_primitives import _GateTextCache
from ..style import DrawStyle
from ..typing import LayoutEngineLike
from ._adaptive_paging import _Managed2DSceneFactory, managed_2d_scene_factory
from .controls import (
    _resolve_2d_slider_layout,
    _style_control_axes,
    _style_slider,
    _style_stepper_button,
    _style_text_box,
)
from .exploration_2d import (
    Managed2DExplorationState,
    WireFilterMode,
    append_wire_fold_markers,
    apply_scene_visual_state,
    clicked_operation_id,
    exploration_control_availability,
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
    visible_expandable_operation_ids,
)
from .shortcut_help import create_shortcut_help_text, toggle_shortcut_help_text
from .slider_2d_windowing import _scene_for_current_window
from .ui_palette import ManagedUiPalette, managed_ui_palette
from .viewport import _figure_size_inches, axes_viewport_pixels

if TYPE_CHECKING:
    from matplotlib.text import Text
    from matplotlib.widgets import Button, Slider, TextBox

    from ..ir.semantic import SemanticCircuitIR
    from ..renderers.matplotlib_renderer import MatplotlibRenderer

_VIEWPORT_EPSILON = 1e-6
_DEFAULT_VISIBLE_QUBITS = 15
_OPTIONAL_CONTROL_BOTTOM = 0.05
_OPTIONAL_CONTROL_HEIGHT = 0.06
_OPTIONAL_CONTROL_RIGHT = 0.97
_OPTIONAL_CONTROL_GAP = 0.01
_WIRE_FILTER_BUTTON_WIDTH = 0.13
_ANCILLA_BUTTON_WIDTH = 0.13
_BLOCK_TOGGLE_BUTTON_WIDTH = 0.18
_MAIN_AXES_ZORDER = 3.0
_SLIDER_CONTROL_ZORDER = 2.0
_OPTIONAL_BUTTON_ZORDER = 1.0

__all__ = [
    "_DEFAULT_VISIBLE_QUBITS",
    "_visible_qubits_viewport_height",
    "Managed2DPageSliderState",
    "Managed2DSliderLayout",
    "configure_page_slider",
    "page_slider_figsize",
    "prepare_page_slider_layout",
    "set_slider_view",
    "slider_viewport_height",
    "slider_viewport_size",
    "slider_viewport_width",
]


@dataclass(frozen=True, slots=True)
class Managed2DSliderLayout:
    """Resolved 2D slider layout and viewport geometry."""

    main_axes_bounds: tuple[float, float, float, float]
    horizontal_axes_bounds: tuple[float, float, float, float] | None
    vertical_axes_bounds: tuple[float, float, float, float] | None
    visible_qubits_axes_bounds: tuple[float, float, float, float] | None
    visible_qubits_decrement_axes_bounds: tuple[float, float, float, float] | None
    visible_qubits_increment_axes_bounds: tuple[float, float, float, float] | None
    viewport_width: float
    viewport_height: float

    @property
    def show_horizontal_slider(self) -> bool:
        return self.horizontal_axes_bounds is not None

    @property
    def show_vertical_slider(self) -> bool:
        return self.vertical_axes_bounds is not None

    @property
    def show_visible_qubits_box(self) -> bool:
        return self.visible_qubits_axes_bounds is not None


@dataclass(slots=True)
class Managed2DPageSliderState:
    """Typed 2D managed-slider state attached to the figure metadata."""

    figure: Figure
    axes: Axes
    circuit: CircuitIR
    layout_engine: LayoutEngineLike
    renderer: MatplotlibRenderer
    style: DrawStyle
    scene_factory: _Managed2DSceneFactory
    full_scene: LayoutScene
    scene: LayoutScene
    column_widths: tuple[float, ...]
    total_scene_width: float
    total_column_count: int
    horizontal_slider: Slider | None
    vertical_slider: Slider | None
    visible_qubits_box: TextBox | None
    visible_qubits_decrement_button: Button | None
    visible_qubits_increment_button: Button | None
    wire_filter_button: Button | None
    ancilla_toggle_button: Button | None
    block_toggle_button: Button | None
    horizontal_axes: Axes | None
    vertical_axes: Axes | None
    visible_qubits_axes: Axes | None
    visible_qubits_decrement_axes: Axes | None
    visible_qubits_increment_axes: Axes | None
    wire_filter_axes: Axes | None
    ancilla_toggle_axes: Axes | None
    block_toggle_axes: Axes | None
    shortcut_help_text: Text | None
    start_column: int
    max_start_column: int
    start_row: int
    max_start_row: int
    viewport_width: float
    viewport_height: float
    viewport_aspect_ratio: float
    total_visible_rows: int
    visible_qubits: int
    allow_figure_resize: bool
    show_visible_qubits_box: bool
    layout: Managed2DSliderLayout | None = None
    horizontal_scene_cache: dict[int, LayoutScene] = field(default_factory=dict)
    window_scene_cache: dict[tuple[int, int], LayoutScene] = field(default_factory=dict)
    text_fit_cache: _GateTextCache = field(default_factory=dict)
    is_syncing_visible_qubits: bool = False
    exploration: Managed2DExplorationState | None = None
    keyboard_shortcuts_enabled: bool = True
    double_click_toggle_enabled: bool = True
    click_callback_id: int | None = None
    key_callback_id: int | None = None

    def show_start_column(self, start_column: int) -> None:
        """Render the requested horizontal start column."""

        self.start_column = int(start_column)
        _apply_2d_slider_state(self)

    def show_start_row(self, start_row: int) -> None:
        """Render the requested vertical start row."""

        self.start_row = int(start_row)
        _apply_2d_slider_state(self)

    def select_operation(self, operation_id: str | None) -> None:
        """Update the contextual selection and redraw the current window."""

        if self.exploration is None:
            return
        self.exploration.selected_operation_id = operation_id
        _apply_2d_slider_state(self)

    def toggle_wire_filter(self) -> None:
        """Toggle between showing all wires and only active wires."""

        if self.exploration is None:
            return
        self.exploration.wire_filter_mode = toggle_wire_filter_mode(
            self.exploration.wire_filter_mode
        )
        _refresh_2d_slider_exploration_context(self)
        _apply_2d_slider_state(self)

    def toggle_ancillas(self) -> None:
        """Toggle whether ancilla-like quantum wires remain visible."""

        if self.exploration is None:
            return
        self.exploration.show_ancillas = not self.exploration.show_ancillas
        _refresh_2d_slider_exploration_context(self)
        _apply_2d_slider_state(self)

    def toggle_selected_block(self) -> None:
        """Expand or collapse the block that owns the current selection."""

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
        _refresh_2d_slider_exploration_context(self)
        _apply_2d_slider_state(self)

    def clear_selection(self) -> None:
        """Clear the current contextual selection."""

        self.select_operation(None)

    def reset_exploration_view(self) -> None:
        """Restore the managed exploration state to its original defaults."""

        if self.exploration is None:
            return
        reset_exploration_state(self.exploration)
        _refresh_2d_slider_exploration_context(self)
        _apply_2d_slider_state(self)

    def toggle_shortcut_help(self) -> None:
        """Toggle the managed shortcut-help overlay."""

        toggle_shortcut_help_text(self.shortcut_help_text, figure=self.figure)

    def step_start_column(self, delta: int) -> None:
        """Move the horizontal window by one managed step."""

        self.show_start_column(self.start_column + delta)

    def step_start_row(self, delta: int) -> None:
        """Move the vertical window by one managed step when it exists."""

        self.show_start_row(self.start_row + delta)

    def show_first_window(self) -> None:
        """Jump to the absolute beginning of the horizontal slider window."""

        self.show_start_column(0)

    def show_last_window(self) -> None:
        """Jump to the absolute end of the horizontal slider window."""

        self.show_start_column(self.max_start_column)

    def step_start_column_large(self, delta: int) -> None:
        """Move the horizontal window by approximately one visible window."""

        if not self.scene.pages:
            self.step_start_column(delta)
            return
        visible_column_count = max(
            1,
            self.scene.pages[0].end_column - self.scene.pages[0].start_column + 1,
        )
        self.show_start_column(self.start_column + (delta * max(1, visible_column_count - 1)))

    def step_expandable_selection(self, *, backwards: bool = False) -> None:
        """Move the selection across visible expandable blocks in visual order."""

        if self.exploration is None:
            return
        visible_operation_ids = visible_expandable_operation_ids(
            self.scene.gates,
            catalog=self.exploration.catalog,
            collapsed_block_ids=self.exploration.collapsed_block_ids,
        )
        next_operation_id = next_visible_operation_selection(
            visible_operation_ids,
            self.exploration.selected_operation_id,
            backwards=backwards,
        )
        if next_operation_id is None:
            return
        self.select_operation(next_operation_id)

    def managed_text_boxes(self) -> tuple[object | None, ...]:
        """Return the managed text inputs that can capture keyboard input."""

        return (self.visible_qubits_box,)


def prepare_page_slider_layout(axes: Axes, scene: LayoutScene) -> Managed2DSliderLayout:
    """Resolve the 2D slider viewport and control placement for one axes."""

    candidate_layouts: list[tuple[int, float, Managed2DSliderLayout]] = []
    for show_horizontal_slider, show_vertical_slider in (
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ):
        layout = _resolve_2d_slider_layout(
            axes,
            show_horizontal_slider=show_horizontal_slider,
            show_vertical_slider=show_vertical_slider,
            show_visible_qubits_box=False,
        )
        viewport_width, viewport_height = slider_viewport_size(axes, scene)
        needs_horizontal_slider = scene.width - viewport_width > _VIEWPORT_EPSILON
        needs_vertical_slider = scene.height - viewport_height > _VIEWPORT_EPSILON
        if not show_horizontal_slider and needs_horizontal_slider:
            continue
        if not show_vertical_slider and needs_vertical_slider:
            continue
        layout = replace(layout, viewport_width=viewport_width, viewport_height=viewport_height)
        slider_count = int(show_horizontal_slider) + int(show_vertical_slider)
        visible_area = viewport_width * viewport_height
        candidate_layouts.append((slider_count, -visible_area, layout))

    if not candidate_layouts:
        layout = _resolve_2d_slider_layout(
            axes,
            show_horizontal_slider=True,
            show_vertical_slider=True,
            show_visible_qubits_box=False,
        )
        viewport_width, viewport_height = slider_viewport_size(axes, scene)
        return replace(
            layout,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )

    _, _, selected_layout = min(candidate_layouts)
    return selected_layout


def configure_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
    set_page_slider: Callable[[Figure, object], None],
    viewport_height: float | None = None,
    layout: Managed2DSliderLayout | None = None,
    quantum_wire_count: int | None = None,
    allow_figure_resize: bool = True,
    initial_visible_qubits: int = _DEFAULT_VISIBLE_QUBITS,
    circuit: CircuitIR | None = None,
    layout_engine: LayoutEngineLike | None = None,
    renderer: MatplotlibRenderer | None = None,
    normalized_style: DrawStyle | None = None,
    semantic_ir: SemanticCircuitIR | None = None,
    expanded_semantic_ir: SemanticCircuitIR | None = None,
    keyboard_shortcuts_enabled: bool = True,
    double_click_toggle_enabled: bool = True,
) -> None:
    """Attach and wire sliders that redraw one discrete 2D window at a time."""

    if circuit is None or layout_engine is None or renderer is None:
        resolved_viewport_height = scene.height if viewport_height is None else viewport_height
        max_scroll_x = max(0.0, scene.width - viewport_width)
        max_scroll_y = max(0.0, scene.height - resolved_viewport_height)
        if max_scroll_x <= 0.0 and max_scroll_y <= 0.0:
            return
        raise ValueError(
            "discrete 2D page slider requires circuit, layout_engine, and renderer context"
        )

    resolved_layout = layout or prepare_page_slider_layout(axes, scene)
    resolved_viewport_width = (
        resolved_layout.viewport_width
        if resolved_layout.viewport_width > _VIEWPORT_EPSILON
        else viewport_width
    )
    resolved_viewport_height = (
        resolved_layout.viewport_height
        if resolved_layout.viewport_height > _VIEWPORT_EPSILON
        else (scene.height if viewport_height is None else viewport_height)
    )

    resolved_style = scene.style if normalized_style is None else normalized_style
    base_normalized_circuit = normalized_draw_circuit(circuit)
    current_semantic = semantic_ir or semantic_circuit_from_circuit_ir(base_normalized_circuit)
    normalized_circuit = normalized_draw_circuit(lower_semantic_circuit(current_semantic))
    scene_factory = managed_2d_scene_factory(
        normalized_circuit,
        layout_engine,
        resolved_style,
        hover_enabled=scene.hover.enabled,
    )
    current_full_scene = scene_factory.scene_for_page_width(float("inf"))
    resolved_visible_row_count = max(
        _scene_visible_row_count(current_full_scene),
        1 if quantum_wire_count is None else quantum_wire_count,
    )
    resolved_visible_qubits = _clamp_visible_qubits(
        initial_visible_qubits,
        resolved_visible_row_count,
    )

    total_scene_width = scene_factory.metrics_for_page_width(float("inf")).scene_width
    initial_viewport_height = _visible_qubits_viewport_height(
        current_full_scene,
        visible_qubits=resolved_visible_qubits,
    )
    initial_viewport_width = min(
        total_scene_width,
        initial_viewport_height
        * max(
            resolved_viewport_width / max(resolved_viewport_height, _VIEWPORT_EPSILON),
            _VIEWPORT_EPSILON,
        ),
    )
    if (
        total_scene_width - initial_viewport_width <= _VIEWPORT_EPSILON
        and resolved_visible_row_count <= resolved_visible_qubits
    ):
        clear_hover_state(axes)
        axes.clear()
        axes.set_position(resolved_layout.main_axes_bounds)
        setattr(axes, "_quantum_circuit_drawer_windowed_clip", False)
        set_viewport_width(figure, viewport_width=scene.width)
        renderer.render(scene, ax=axes)
        return

    exploration = managed_exploration_state(
        current_semantic,
        expanded_semantic_ir or current_semantic,
    )
    exploration.transformed_semantic_ir = current_semantic

    state = Managed2DPageSliderState(
        figure=figure,
        axes=axes,
        circuit=normalized_circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        style=resolved_style,
        scene_factory=scene_factory,
        full_scene=current_full_scene,
        scene=current_full_scene,
        column_widths=tuple(scene_factory.paging_inputs.column_widths),
        total_scene_width=total_scene_width,
        total_column_count=len(normalized_circuit.layers),
        horizontal_slider=None,
        vertical_slider=None,
        visible_qubits_box=None,
        visible_qubits_decrement_button=None,
        visible_qubits_increment_button=None,
        wire_filter_button=None,
        ancilla_toggle_button=None,
        block_toggle_button=None,
        horizontal_axes=None,
        vertical_axes=None,
        visible_qubits_axes=None,
        visible_qubits_decrement_axes=None,
        visible_qubits_increment_axes=None,
        wire_filter_axes=None,
        ancilla_toggle_axes=None,
        block_toggle_axes=None,
        shortcut_help_text=None,
        start_column=0,
        max_start_column=0,
        start_row=0,
        max_start_row=0,
        viewport_width=initial_viewport_width,
        viewport_height=initial_viewport_height,
        viewport_aspect_ratio=(
            resolved_viewport_width / resolved_viewport_height
            if resolved_viewport_height > 0.0
            else 1.0
        ),
        total_visible_rows=resolved_visible_row_count,
        visible_qubits=resolved_visible_qubits,
        allow_figure_resize=allow_figure_resize,
        show_visible_qubits_box=resolved_visible_row_count > _DEFAULT_VISIBLE_QUBITS,
        layout=None,
        exploration=exploration,
        keyboard_shortcuts_enabled=keyboard_shortcuts_enabled,
        double_click_toggle_enabled=double_click_toggle_enabled,
    )
    set_page_slider(figure, state)
    state.shortcut_help_text = create_shortcut_help_text(
        figure,
        palette=managed_ui_palette(current_full_scene.style.theme),
        lines=(
            "View",
            "Left/Right: Move columns",
            "Up/Down: Move wire rows",
            "Home/End: Jump to first/last columns",
            "PageUp/PageDown: Jump by visible window",
            "+/-: Show more/fewer wires",
            "w: Toggle wires all/active",
            "",
            "Selection",
            "Tab/Shift+Tab: Move between blocks",
            "Enter/Space: Toggle block",
            "Esc: Clear selection",
            "0: Reset exploration",
            "?: Show/hide this help",
        ),
    )
    _attach_slider_selection_clicks(state)
    _attach_slider_key_shortcuts(state)
    _apply_2d_slider_state(state)
    _sync_visible_qubits_box(state, state.visible_qubits)


def page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    """Return a readable managed figure size for page-slider mode."""

    width = max(4.8, viewport_width * 0.98)
    height = max(2.0, scene_height * 0.68) + 1.0
    return width, height


def slider_viewport_size(axes: Axes, scene: LayoutScene) -> tuple[float, float]:
    """Estimate the visible 2D viewport using equal X/Y scaling."""

    axes_width_pixels, axes_height_pixels = axes_viewport_pixels(axes)
    if axes_width_pixels <= 0.0 or axes_height_pixels <= 0.0:
        return scene.width, scene.height
    axes_ratio = axes_width_pixels / axes_height_pixels
    full_height_viewport_width = min(scene.width, scene.height * axes_ratio)
    uncapped_figure_width, uncapped_figure_height = page_slider_figsize(
        full_height_viewport_width,
        scene.height,
    )
    figure_width_inches, figure_height_inches = _figure_size_inches(axes.figure)
    compact_scale = min(
        1.0,
        figure_width_inches / uncapped_figure_width if uncapped_figure_width > 0.0 else 1.0,
        figure_height_inches / uncapped_figure_height if uncapped_figure_height > 0.0 else 1.0,
    )
    viewport_height = min(scene.height, scene.height * compact_scale)
    viewport_width = viewport_height * axes_ratio
    if viewport_width > scene.width:
        viewport_width = scene.width
        viewport_height = min(scene.height, viewport_width / axes_ratio)
    return viewport_width, viewport_height


def slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene width for the current slider viewport."""

    return slider_viewport_size(axes, scene)[0]


def slider_viewport_height(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene height for the current slider viewport."""

    return slider_viewport_size(axes, scene)[1]


def set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
    y_offset: float = 0.0,
    viewport_height: float | None = None,
) -> None:
    """Set the 2D axes limits used for the slider viewport."""

    resolved_viewport_height = scene.height if viewport_height is None else viewport_height
    max_x_offset = max(0.0, scene.width - viewport_width)
    max_y_offset = max(0.0, scene.height - resolved_viewport_height)
    resolved_x_offset = min(max(0.0, x_offset), max_x_offset)
    resolved_y_offset = min(max(0.0, y_offset), max_y_offset)
    axes.set_xlim(resolved_x_offset, resolved_x_offset + viewport_width)
    axes.set_ylim(resolved_y_offset + resolved_viewport_height, resolved_y_offset)


def _apply_2d_slider_state(state: Managed2DPageSliderState) -> None:
    max_start_column = max(0, state.total_column_count - 1)
    state.max_start_column = max_start_column if _has_horizontal_overflow(state) else 0
    state.max_start_row = max(0, state.total_visible_rows - state.visible_qubits)
    state.start_column = min(max(0, state.start_column), state.max_start_column)
    state.start_row = min(max(0, state.start_row), state.max_start_row)
    layout = _resolve_2d_slider_layout(
        state.axes,
        show_horizontal_slider=state.max_start_column > 0,
        show_vertical_slider=state.max_start_row > 0,
        show_visible_qubits_box=state.show_visible_qubits_box,
    )
    rebuild_controls = _needs_2d_control_rebuild(state, layout)
    if rebuild_controls:
        _remove_2d_controls(state)
    window_scene = _scene_for_current_window(state)
    state.scene = _styled_slider_scene(state, window_scene)
    clear_hover_state(state.axes)
    state.axes.clear()
    state.axes.set_position(layout.main_axes_bounds)
    state.axes.set_zorder(_MAIN_AXES_ZORDER)
    setattr(state.axes, "_quantum_circuit_drawer_windowed_clip", True)
    set_viewport_width(state.figure, viewport_width=state.viewport_width)
    state.renderer._render_2d_scene(
        state.scene,
        axes=state.axes,
        output=None,
        gate_text_cache=state.text_fit_cache,
    )
    set_slider_view(
        state.axes,
        state.scene,
        x_offset=0.0,
        viewport_width=state.viewport_width,
        y_offset=0.0,
        viewport_height=state.viewport_height,
    )
    if rebuild_controls:
        _attach_2d_controls(state, layout)
    state.layout = layout
    _sync_horizontal_slider(state)
    _sync_vertical_slider(state)
    _sync_visible_qubits_box(state, state.visible_qubits)
    _sync_exploration_buttons(state)
    canvas = getattr(state.figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


def _attach_2d_controls(
    state: Managed2DPageSliderState,
    layout: Managed2DSliderLayout,
) -> None:
    from matplotlib.widgets import Button, Slider, TextBox

    theme = state.style.theme
    palette = managed_ui_palette(theme)

    if state.max_start_column > 0 and layout.horizontal_axes_bounds is not None:
        horizontal_axes = state.figure.add_axes(
            layout.horizontal_axes_bounds,
            facecolor=palette.surface_facecolor,
        )
        horizontal_axes.set_zorder(_SLIDER_CONTROL_ZORDER)
        _style_control_axes(horizontal_axes, palette=palette)
        horizontal_slider = Slider(
            ax=horizontal_axes,
            label="",
            valmin=0.0,
            valmax=float(state.max_start_column),
            valinit=float(state.start_column),
            valstep=1.0,
            color=palette.slider_fill_color,
            track_color=palette.slider_track_color,
            handle_style={
                "facecolor": palette.accent_color,
                "edgecolor": palette.accent_edgecolor,
                "size": 16,
            },
        )
        _style_slider(horizontal_slider, palette=palette)
        horizontal_slider.on_changed(lambda value: state.show_start_column(round(float(value))))
        state.horizontal_slider = horizontal_slider
        state.horizontal_axes = horizontal_axes

    if state.max_start_row > 0 and layout.vertical_axes_bounds is not None:
        vertical_axes = state.figure.add_axes(
            layout.vertical_axes_bounds,
            facecolor=palette.surface_facecolor,
        )
        vertical_axes.set_zorder(_SLIDER_CONTROL_ZORDER)
        _style_control_axes(vertical_axes, palette=palette)
        vertical_slider = Slider(
            ax=vertical_axes,
            label="",
            valmin=0.0,
            valmax=float(state.max_start_row),
            valinit=_vertical_slider_value_for_start_row(state, state.start_row),
            valstep=1.0,
            orientation="vertical",
            color=palette.slider_fill_color,
            track_color=palette.slider_track_color,
            handle_style={
                "facecolor": palette.accent_color,
                "edgecolor": palette.accent_edgecolor,
                "size": 12,
            },
        )
        _style_slider(vertical_slider, palette=palette)
        vertical_slider.on_changed(
            lambda value: state.show_start_row(_start_row_for_vertical_slider_value(state, value))
        )
        state.vertical_slider = vertical_slider
        state.vertical_axes = vertical_axes

    if state.show_visible_qubits_box and layout.visible_qubits_axes_bounds is not None:
        visible_qubits_axes = state.figure.add_axes(
            layout.visible_qubits_axes_bounds,
            facecolor=palette.surface_facecolor,
        )
        visible_qubits_axes.set_zorder(_SLIDER_CONTROL_ZORDER)
        _style_control_axes(visible_qubits_axes, palette=palette)
        visible_qubits_box = TextBox(
            visible_qubits_axes,
            "",
            initial=str(state.visible_qubits),
            color=palette.surface_facecolor,
            hovercolor=palette.surface_hover_facecolor,
            textalignment="center",
        )
        _style_text_box(
            visible_qubits_box,
            text_color=palette.text_color,
            border_color=palette.surface_edgecolor,
            facecolor=palette.surface_facecolor,
        )
        visible_qubits_box.on_submit(lambda text: _handle_visible_qubits_submit(state, text))
        state.visible_qubits_box = visible_qubits_box
        state.visible_qubits_axes = visible_qubits_axes
        if layout.visible_qubits_increment_axes_bounds is not None:
            visible_qubits_increment_axes = state.figure.add_axes(
                layout.visible_qubits_increment_axes_bounds,
                facecolor=palette.surface_facecolor,
            )
            visible_qubits_increment_axes.set_zorder(_SLIDER_CONTROL_ZORDER)
            _style_control_axes(visible_qubits_increment_axes, palette=palette)
            visible_qubits_increment_button = Button(
                visible_qubits_increment_axes,
                "\u25b4",
                color=palette.surface_facecolor,
                hovercolor=palette.surface_hover_facecolor,
            )
            _style_stepper_button(visible_qubits_increment_button, palette=palette)
            visible_qubits_increment_button.on_clicked(
                lambda _: _set_visible_qubits(state, state.visible_qubits + 1)
            )
            state.visible_qubits_increment_button = visible_qubits_increment_button
            state.visible_qubits_increment_axes = visible_qubits_increment_axes
        if layout.visible_qubits_decrement_axes_bounds is not None:
            visible_qubits_decrement_axes = state.figure.add_axes(
                layout.visible_qubits_decrement_axes_bounds,
                facecolor=palette.surface_facecolor,
            )
            visible_qubits_decrement_axes.set_zorder(_SLIDER_CONTROL_ZORDER)
            _style_control_axes(visible_qubits_decrement_axes, palette=palette)
            visible_qubits_decrement_button = Button(
                visible_qubits_decrement_axes,
                "\u25be",
                color=palette.surface_facecolor,
                hovercolor=palette.surface_hover_facecolor,
            )
            _style_stepper_button(visible_qubits_decrement_button, palette=palette)
            visible_qubits_decrement_button.on_clicked(
                lambda _: _set_visible_qubits(state, state.visible_qubits - 1)
            )
            state.visible_qubits_decrement_button = visible_qubits_decrement_button
            state.visible_qubits_decrement_axes = visible_qubits_decrement_axes

    button_bounds = _slider_exploration_button_bounds(state)
    if "wire_filter" in button_bounds:
        wire_filter_axes = state.figure.add_axes(
            button_bounds["wire_filter"],
            facecolor=palette.surface_facecolor,
        )
        wire_filter_axes.set_zorder(_OPTIONAL_BUTTON_ZORDER)
        _style_control_axes(wire_filter_axes, palette=palette)
        wire_filter_button = Button(
            wire_filter_axes,
            "",
            color=palette.surface_facecolor,
            hovercolor=palette.surface_hover_facecolor,
        )
        _style_stepper_button(wire_filter_button, palette=palette)
        wire_filter_button.on_clicked(lambda _: state.toggle_wire_filter())
        state.wire_filter_button = wire_filter_button
        state.wire_filter_axes = wire_filter_axes

    if "ancilla" in button_bounds:
        ancilla_toggle_axes = state.figure.add_axes(
            button_bounds["ancilla"],
            facecolor=palette.surface_facecolor,
        )
        ancilla_toggle_axes.set_zorder(_OPTIONAL_BUTTON_ZORDER)
        _style_control_axes(ancilla_toggle_axes, palette=palette)
        ancilla_toggle_button = Button(
            ancilla_toggle_axes,
            "",
            color=palette.surface_facecolor,
            hovercolor=palette.surface_hover_facecolor,
        )
        _style_stepper_button(ancilla_toggle_button, palette=palette)
        ancilla_toggle_button.on_clicked(lambda _: state.toggle_ancillas())
        state.ancilla_toggle_button = ancilla_toggle_button
        state.ancilla_toggle_axes = ancilla_toggle_axes

    if "block" in button_bounds:
        block_toggle_axes = state.figure.add_axes(
            button_bounds["block"],
            facecolor=palette.surface_facecolor,
        )
        block_toggle_axes.set_zorder(_OPTIONAL_BUTTON_ZORDER)
        _style_control_axes(block_toggle_axes, palette=palette)
        block_toggle_button = Button(
            block_toggle_axes,
            "",
            color=palette.surface_facecolor,
            hovercolor=palette.surface_hover_facecolor,
        )
        _style_stepper_button(block_toggle_button, palette=palette)
        block_toggle_button.on_clicked(lambda _: state.toggle_selected_block())
        state.block_toggle_button = block_toggle_button
        state.block_toggle_axes = block_toggle_axes


def _remove_2d_controls(state: Managed2DPageSliderState) -> None:
    for widget in (
        state.horizontal_slider,
        state.vertical_slider,
        state.visible_qubits_box,
        state.visible_qubits_decrement_button,
        state.visible_qubits_increment_button,
        state.wire_filter_button,
        state.ancilla_toggle_button,
        state.block_toggle_button,
    ):
        if widget is not None and hasattr(widget, "disconnect_events"):
            widget.disconnect_events()

    for axes in (
        state.horizontal_axes,
        state.vertical_axes,
        state.visible_qubits_axes,
        state.visible_qubits_decrement_axes,
        state.visible_qubits_increment_axes,
        state.wire_filter_axes,
        state.ancilla_toggle_axes,
        state.block_toggle_axes,
    ):
        if axes is not None:
            axes.remove()

    state.horizontal_slider = None
    state.vertical_slider = None
    state.visible_qubits_box = None
    state.visible_qubits_decrement_button = None
    state.visible_qubits_increment_button = None
    state.horizontal_axes = None
    state.vertical_axes = None
    state.visible_qubits_axes = None
    state.visible_qubits_decrement_axes = None
    state.visible_qubits_increment_axes = None
    state.wire_filter_button = None
    state.ancilla_toggle_button = None
    state.block_toggle_button = None
    state.wire_filter_axes = None
    state.ancilla_toggle_axes = None
    state.block_toggle_axes = None
    state.layout = None


def _handle_visible_qubits_submit(
    state: Managed2DPageSliderState,
    text: str,
) -> None:
    if state.is_syncing_visible_qubits:
        return

    try:
        requested_visible_qubits = int(text.strip())
    except ValueError:
        _sync_visible_qubits_box(state, state.visible_qubits)
        return

    _set_visible_qubits(state, requested_visible_qubits)


def _set_visible_qubits(
    state: Managed2DPageSliderState,
    requested_visible_qubits: int,
) -> None:
    resolved_visible_qubits = _clamp_visible_qubits(
        requested_visible_qubits,
        state.total_visible_rows,
    )
    state.visible_qubits = resolved_visible_qubits
    state.viewport_height = _visible_qubits_viewport_height(
        state.full_scene,
        visible_qubits=resolved_visible_qubits,
    )
    state.viewport_width = min(
        state.total_scene_width,
        state.viewport_height * max(state.viewport_aspect_ratio, _VIEWPORT_EPSILON),
    )
    if state.viewport_height > _VIEWPORT_EPSILON:
        state.viewport_aspect_ratio = state.viewport_width / state.viewport_height
    state.horizontal_scene_cache.clear()
    state.window_scene_cache.clear()
    state.layout = None
    if state.allow_figure_resize:
        figure_width, figure_height = page_slider_figsize(
            state.viewport_width,
            state.viewport_height,
        )
        state.figure.set_size_inches(figure_width, figure_height, forward=True)
    _apply_2d_slider_state(state)
    _sync_visible_qubits_box(state, resolved_visible_qubits)


def _sync_visible_qubits_box(
    state: Managed2DPageSliderState,
    visible_qubits: int,
) -> None:
    if state.visible_qubits_box is None:
        return

    state.is_syncing_visible_qubits = True
    try:
        state.visible_qubits_box.set_val(str(visible_qubits))
    finally:
        state.is_syncing_visible_qubits = False


def _sync_horizontal_slider(state: Managed2DPageSliderState) -> None:
    if state.horizontal_slider is None:
        return
    _set_slider_value_silently(state.horizontal_slider, float(state.start_column))


def _sync_vertical_slider(state: Managed2DPageSliderState) -> None:
    if state.vertical_slider is None:
        return
    _set_slider_value_silently(
        state.vertical_slider,
        _vertical_slider_value_for_start_row(state, state.start_row),
    )


def _set_slider_value_silently(slider: Slider, value: float) -> None:
    if float(slider.val) == float(value):
        return

    previous_event_state = slider.eventson
    slider.eventson = False
    try:
        slider.set_val(float(value))
    finally:
        slider.eventson = previous_event_state


def _vertical_slider_value_for_start_row(
    state: Managed2DPageSliderState,
    start_row: int,
) -> float:
    return float(state.max_start_row - min(max(0, start_row), state.max_start_row))


def _start_row_for_vertical_slider_value(
    state: Managed2DPageSliderState,
    value: float,
) -> int:
    resolved_value = round(float(value))
    return min(max(0, state.max_start_row - resolved_value), state.max_start_row)


def _visible_qubits_viewport_height(
    scene: LayoutScene,
    *,
    visible_qubits: int,
) -> float:
    resolved_visible_qubits = max(1, visible_qubits)
    wire_positions = sorted(wire.y for wire in scene.wires)
    if not wire_positions:
        return scene.height

    largest_window_span = max(
        wire_positions[index + resolved_visible_qubits - 1] - wire_positions[index]
        for index in range(len(wire_positions) - resolved_visible_qubits + 1)
    )
    style = scene.style
    return min(scene.height, style.margin_top + style.margin_bottom + largest_window_span)


def _clamp_visible_qubits(
    visible_qubits: int,
    total_visible_rows: int | None,
) -> int:
    resolved_total_visible_rows = max(1, 1 if total_visible_rows is None else total_visible_rows)
    return min(max(1, visible_qubits), resolved_total_visible_rows)


def _scene_visible_row_count(scene: LayoutScene) -> int:
    return max(1, len(scene.wires))


def _needs_2d_control_rebuild(
    state: Managed2DPageSliderState,
    layout: Managed2DSliderLayout,
) -> bool:
    if state.layout is None:
        return True

    if state.layout.horizontal_axes_bounds != layout.horizontal_axes_bounds:
        return True
    if state.layout.vertical_axes_bounds != layout.vertical_axes_bounds:
        return True
    if state.layout.visible_qubits_axes_bounds != layout.visible_qubits_axes_bounds:
        return True
    if (
        state.layout.visible_qubits_decrement_axes_bounds
        != layout.visible_qubits_decrement_axes_bounds
    ):
        return True
    if (
        state.layout.visible_qubits_increment_axes_bounds
        != layout.visible_qubits_increment_axes_bounds
    ):
        return True

    if (state.horizontal_slider is None) != (layout.horizontal_axes_bounds is None):
        return True
    if (state.vertical_slider is None) != (layout.vertical_axes_bounds is None):
        return True
    if (state.visible_qubits_box is None) != (layout.visible_qubits_axes_bounds is None):
        return True
    if (state.visible_qubits_decrement_button is None) != (
        layout.visible_qubits_decrement_axes_bounds is None
    ):
        return True
    if (state.visible_qubits_increment_button is None) != (
        layout.visible_qubits_increment_axes_bounds is None
    ):
        return True
    desired_optional_buttons = _slider_exploration_button_bounds(state)
    optional_button_presence = {
        "wire_filter": state.wire_filter_button is not None and state.wire_filter_axes is not None,
        "ancilla": state.ancilla_toggle_button is not None
        and state.ancilla_toggle_axes is not None,
        "block": state.block_toggle_button is not None and state.block_toggle_axes is not None,
    }
    for button_name, is_present in optional_button_presence.items():
        if is_present != (button_name in desired_optional_buttons):
            return True

    if state.horizontal_slider is not None and state.horizontal_slider.valmax != float(
        state.max_start_column
    ):
        return True

    return state.vertical_slider is not None and state.vertical_slider.valmax != float(
        state.max_start_row
    )


def _has_horizontal_overflow(state: Managed2DPageSliderState) -> bool:
    return state.total_scene_width - state.viewport_width > _VIEWPORT_EPSILON


def _refresh_2d_slider_exploration_context(state: Managed2DPageSliderState) -> None:
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
    state.scene_factory = managed_2d_scene_factory(
        normalized_circuit,
        state.layout_engine,
        state.style,
        hover_enabled=state.full_scene.hover.enabled,
    )
    state.column_widths = tuple(state.scene_factory.paging_inputs.column_widths)
    state.total_scene_width = state.scene_factory.metrics_for_page_width(float("inf")).scene_width
    state.total_column_count = len(normalized_circuit.layers)
    state.full_scene = state.scene_factory.scene_for_page_width(float("inf"))
    state.total_visible_rows = _scene_visible_row_count(state.full_scene)
    state.visible_qubits = _clamp_visible_qubits(state.visible_qubits, state.total_visible_rows)
    state.viewport_height = _visible_qubits_viewport_height(
        state.full_scene,
        visible_qubits=state.visible_qubits,
    )
    state.viewport_width = min(
        state.total_scene_width,
        state.viewport_height * max(state.viewport_aspect_ratio, _VIEWPORT_EPSILON),
    )
    state.horizontal_scene_cache.clear()
    state.window_scene_cache.clear()
    state.layout = None


def _styled_slider_scene(
    state: Managed2DPageSliderState,
    scene: LayoutScene,
) -> LayoutScene:
    if state.exploration is None or state.exploration.transformed_semantic_ir is None:
        return scene

    styled_scene = apply_scene_visual_state(
        scene,
        state.exploration.transformed_semantic_ir,
        selected_operation_id=state.exploration.selected_operation_id,
    )
    return append_wire_fold_markers(
        styled_scene,
        state.exploration.hidden_wire_ranges,
    )


def _attach_slider_selection_clicks(state: Managed2DPageSliderState) -> None:
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
        operation_id = clicked_operation_id(state.axes, state.scene, event)
        if state.double_click_toggle_enabled and event.dblclick:
            toggle_operation_with_selection(state, operation_id)
            return
        state.select_operation(operation_id)

    state.click_callback_id = int(canvas.mpl_connect("button_press_event", _handle_click))


def _attach_slider_key_shortcuts(state: Managed2DPageSliderState) -> None:
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
            _run(state.show_first_window)
            return
        if is_end_key(event):
            _run(state.show_last_window)
            return
        if is_page_up_key(event):
            _run(lambda: state.step_start_column_large(-1))
            return
        if is_page_down_key(event):
            _run(lambda: state.step_start_column_large(1))
            return
        if is_plus_key(event):
            _run(lambda: _set_visible_qubits(state, state.visible_qubits + 1))
            return
        if is_minus_key(event):
            _run(lambda: _set_visible_qubits(state, state.visible_qubits - 1))
            return
        if is_next_selection_key(event):
            _run(state.step_expandable_selection)
            return
        if is_previous_selection_key(event):
            _run(lambda: state.step_expandable_selection(backwards=True))
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
            _run(lambda: state.step_start_column(-1))
            return
        if key_name == "right":
            _run(lambda: state.step_start_column(1))
            return
        if key_name == "up":
            if state.max_start_row > 0:
                _run(lambda: state.step_start_row(-1))
            return
        if key_name == "down":
            if state.max_start_row > 0:
                _run(lambda: state.step_start_row(1))
            return
        if is_block_toggle_key(event):
            _run(state.toggle_selected_block)

    state.key_callback_id = int(canvas.mpl_connect("key_press_event", _handle_key))


def _slider_exploration_button_bounds(
    state: Managed2DPageSliderState,
) -> dict[str, tuple[float, float, float, float]]:
    if state.exploration is None:
        return {}

    availability = exploration_control_availability(
        state.exploration.catalog,
        collapsed_block_ids=state.exploration.collapsed_block_ids,
        wire_filter_mode=state.exploration.wire_filter_mode,
        show_ancillas=state.exploration.show_ancillas,
        selected_operation_id=state.exploration.selected_operation_id,
    )
    ordered_buttons: list[tuple[str, float]] = []
    if availability.show_block_toggle:
        ordered_buttons.append(("block", _BLOCK_TOGGLE_BUTTON_WIDTH))
    if availability.show_wire_filter:
        ordered_buttons.append(("wire_filter", _WIRE_FILTER_BUTTON_WIDTH))
    if availability.show_ancilla_toggle:
        ordered_buttons.append(("ancilla", _ANCILLA_BUTTON_WIDTH))

    right = _OPTIONAL_CONTROL_RIGHT
    bounds: dict[str, tuple[float, float, float, float]] = {}
    for button_name, width in reversed(ordered_buttons):
        bounds[button_name] = (
            right - width,
            _OPTIONAL_CONTROL_BOTTOM,
            width,
            _OPTIONAL_CONTROL_HEIGHT,
        )
        right -= width + _OPTIONAL_CONTROL_GAP
    return bounds


def _sync_exploration_buttons(state: Managed2DPageSliderState) -> None:
    if state.exploration is None:
        return

    palette = managed_ui_palette(state.style.theme)
    if state.wire_filter_button is not None:
        state.wire_filter_button.label.set_text(
            "Wires: Active"
            if state.exploration.wire_filter_mode is WireFilterMode.ACTIVE
            else "Wires: All"
        )
        state.wire_filter_button.label.set_fontsize(9.0)
        _set_button_enabled(
            state.wire_filter_button,
            enabled=True,
            palette=palette,
        )

    if state.ancilla_toggle_button is not None:
        state.ancilla_toggle_button.label.set_text(
            "Ancillas: Show" if state.exploration.show_ancillas else "Ancillas: Hide"
        )
        state.ancilla_toggle_button.label.set_fontsize(8.5)
        _set_button_enabled(
            state.ancilla_toggle_button,
            enabled=True,
            palette=palette,
        )

    block_action = selected_block_action(
        state.exploration.catalog,
        selected_operation_id=state.exploration.selected_operation_id,
        collapsed_block_ids=state.exploration.collapsed_block_ids,
    )
    if state.block_toggle_button is not None:
        state.block_toggle_button.label.set_text("" if block_action is None else block_action.label)
        state.block_toggle_button.label.set_fontsize(8.3)
        _set_button_enabled(
            state.block_toggle_button,
            enabled=block_action is not None,
            palette=palette,
        )


def _set_button_enabled(
    button: Button,
    *,
    enabled: bool,
    palette: ManagedUiPalette,
) -> None:
    button.ax.set_facecolor(
        palette.surface_facecolor if enabled else palette.surface_facecolor_disabled
    )
    button.color = palette.surface_facecolor if enabled else palette.surface_facecolor_disabled
    button.hovercolor = (
        palette.surface_hover_facecolor if enabled else palette.surface_facecolor_disabled
    )
    button.label.set_color(palette.text_color if enabled else palette.disabled_text_color)
    for spine in button.ax.spines.values():
        spine.set_color(
            palette.surface_edgecolor_active if enabled else palette.surface_edgecolor_disabled
        )
        spine.set_linewidth(1.0)
