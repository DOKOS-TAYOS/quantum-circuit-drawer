"""Managed 3D slider state and orchestration helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from matplotlib.axes import Axes
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.figure import Figure

from ..drawing.pipeline import PreparedDrawPipeline, _compute_3d_scene
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.semantic import semantic_operation_id
from ..layout._layering import normalized_draw_circuit
from ..layout._layout_scaffold import build_layout_paging_inputs, paged_scene_metrics_for_width
from ..layout.scene_3d import LayoutScene3D
from ..renderers._matplotlib_figure import (
    clear_hover_state,
    clicked_artist_operation_id,
)
from ..style import DrawStyle
from ..typing import LayoutEngine3DLike
from .controls import (
    _style_control_axes,
    _style_slider,
    _style_stepper_button,
    apply_managed_3d_axes_bounds,
    managed_3d_axes_bounds,
)
from .exploration_2d import (
    Managed2DExplorationState,
    WireFilterMode,
    apply_scene_visual_state_3d,
    exploration_control_availability,
    managed_exploration_state,
    next_selected_operation_id_for_block_action,
    selected_block_action,
    toggle_wire_filter_mode,
    transform_semantic_circuit,
)
from .interaction import (
    is_block_toggle_key,
    managed_key_name,
    toggle_operation_with_selection,
)
from .ui_palette import ManagedUiPalette, managed_ui_palette
from .view_state_3d import (
    _MANAGED_3D_FIXED_VIEW_STATE_ATTR,
    capture_managed_3d_view_state,
)
from .viewport import _figure_size_inches

if TYPE_CHECKING:
    from matplotlib.widgets import Button, Slider
    from mpl_toolkits.mplot3d.axes3d import Axes3D  # type: ignore[import-untyped]

    from ..layout.topology_3d import TopologyName

_MANAGED_3D_SLIDER_BOUNDS = (0.18, 0.09, 0.72, 0.05)
_OPTIONAL_CONTROL_BOTTOM = 0.025
_OPTIONAL_CONTROL_HEIGHT = 0.045
_OPTIONAL_CONTROL_RIGHT = 0.97
_OPTIONAL_CONTROL_GAP = 0.01
_WIRE_FILTER_BUTTON_WIDTH = 0.13
_ANCILLA_BUTTON_WIDTH = 0.13
_BLOCK_TOGGLE_BUTTON_WIDTH = 0.18
_SLIDER_CONTROL_ZORDER = 2.0
_OPTIONAL_BUTTON_ZORDER = 1.0
_CLICK_RELEASE_MAX_DRAG_PIXELS = 6.0


@dataclass(slots=True)
class Managed3DPageSliderState:
    """Typed 3D managed-slider state attached to the figure metadata."""

    figure: Figure
    axes: Axes3D
    pipeline: PreparedDrawPipeline
    current_scene: LayoutScene3D
    horizontal_slider: Slider | None
    horizontal_axes: Axes | None
    start_column: int
    window_size: int
    max_start_column: int
    scene_cache: dict[int, LayoutScene3D]
    vertical_slider: Slider | None = None
    vertical_axes: Axes | None = None
    ui_palette: ManagedUiPalette | None = None
    wire_filter_button: Button | None = None
    ancilla_toggle_button: Button | None = None
    block_toggle_button: Button | None = None
    wire_filter_axes: Axes | None = None
    ancilla_toggle_axes: Axes | None = None
    block_toggle_axes: Axes | None = None
    exploration: Managed2DExplorationState | None = None
    keyboard_shortcuts_enabled: bool = True
    double_click_toggle_enabled: bool = True
    click_press_callback_id: int | None = None
    click_release_callback_id: int | None = None
    key_callback_id: int | None = None
    pending_click: tuple[float, float, bool] | None = None

    def show_start_column(self, start_column: int) -> None:
        """Render the requested 3D column window on the managed axes."""

        resolved_start_column = min(max(0, start_column), self.max_start_column)
        scene = self._scene_for_start_column(resolved_start_column)
        self.start_column = resolved_start_column
        self.current_scene = scene

        fixed_view_state = capture_managed_3d_view_state(self.axes)
        clear_hover_state(self.axes)
        self.axes.clear()
        setattr(self.axes, _MANAGED_3D_FIXED_VIEW_STATE_ATTR, fixed_view_state)
        apply_managed_3d_axes_bounds(self.axes, has_page_slider=True)
        self.pipeline.renderer.render(scene, ax=self.axes)
        _ensure_3d_slider_exploration_controls(self)
        _sync_3d_slider_exploration_buttons(self)

        canvas = getattr(self.figure, "canvas", None)
        if canvas is not None:
            canvas.draw_idle()

    def select_topology(self, topology: TopologyName) -> None:
        """Switch topology while keeping the current column window."""

        updated_draw_options = replace(self.pipeline.draw_options, topology=topology)
        self.pipeline = replace(self.pipeline, draw_options=updated_draw_options)
        self.scene_cache.clear()
        _refresh_3d_slider_window_metrics(self)
        self.show_start_column(self.start_column)

    def select_operation(self, operation_id: str | None) -> None:
        """Update the contextual selection and redraw the current slider view."""

        if self.exploration is None:
            return
        self.exploration.selected_operation_id = operation_id
        self.scene_cache.clear()
        self.show_start_column(self.start_column)

    def toggle_wire_filter(self) -> None:
        """Toggle between showing all wires and only active wires."""

        if self.exploration is None:
            return
        self.exploration.wire_filter_mode = toggle_wire_filter_mode(
            self.exploration.wire_filter_mode
        )
        _refresh_3d_slider_exploration_context(self)
        self.show_start_column(self.start_column)

    def toggle_ancillas(self) -> None:
        """Toggle whether ancilla-like quantum wires remain visible."""

        if self.exploration is None:
            return
        self.exploration.show_ancillas = not self.exploration.show_ancillas
        _refresh_3d_slider_exploration_context(self)
        self.show_start_column(self.start_column)

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
        _refresh_3d_slider_exploration_context(self)
        self.show_start_column(self.start_column)

    def step_start_column(self, delta: int) -> None:
        """Move the managed 3D window by one column step."""

        self.show_start_column(self.start_column + delta)

    def _scene_for_start_column(self, start_column: int) -> LayoutScene3D:
        cached_scene = self.scene_cache.get(start_column)
        if cached_scene is not None:
            return cached_scene

        windowed_circuit = circuit_window(
            self.pipeline.ir,
            start_column=start_column,
            window_size=self.window_size,
        )
        scene = _compute_3d_scene(
            cast("LayoutEngine3DLike", self.pipeline.layout_engine),
            windowed_circuit,
            self.pipeline.normalized_style,
            topology_name=self.pipeline.draw_options.topology,
            direct=self.pipeline.draw_options.direct,
            hover_enabled=self.pipeline.draw_options.hover.enabled,
            topology_qubits=self.pipeline.draw_options.topology_qubits,
            topology_resize=self.pipeline.draw_options.topology_resize,
        )
        if self.exploration is not None and self.exploration.transformed_semantic_ir is not None:
            scene = apply_scene_visual_state_3d(
                scene,
                self.exploration.transformed_semantic_ir,
                selected_operation_id=self.exploration.selected_operation_id,
            )
        self.scene_cache[start_column] = scene
        return scene


def configure_3d_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    set_page_slider: Callable[[Figure, object], None],
    keyboard_shortcuts_enabled: bool = True,
    double_click_toggle_enabled: bool = True,
) -> Managed3DPageSliderState | None:
    """Attach and wire a managed 3D slider that moves through circuit columns."""

    from .page_window_3d_ranges import windowed_3d_page_ranges

    normalized_pipeline = replace(
        pipeline,
        ir=normalized_draw_circuit(lower_semantic_circuit(pipeline.semantic_ir)),
    )
    total_columns = len(normalized_pipeline.ir.layers)
    page_ranges = windowed_3d_page_ranges(
        normalized_pipeline,
        figure_size=_figure_size_inches(figure),
        axes_bounds=managed_3d_axes_bounds(has_page_slider=True),
    )
    first_page_start, first_page_end = page_ranges[0]
    window_size = max(1, first_page_end - first_page_start + 1)
    max_start_column = max(0, total_columns - window_size)
    if max_start_column <= 0:
        return None

    from matplotlib.widgets import Slider

    axes_3d = cast("Axes3D", axes)
    apply_managed_3d_axes_bounds(axes, has_page_slider=True)
    slider_axes = figure.add_axes(_MANAGED_3D_SLIDER_BOUNDS)
    palette = managed_ui_palette(cast("LayoutScene3D", pipeline.paged_scene).style.theme)
    slider_axes.set_zorder(_SLIDER_CONTROL_ZORDER)
    _style_control_axes(slider_axes, palette=palette)
    exploration = managed_exploration_state(
        normalized_pipeline.semantic_ir,
        normalized_pipeline.expanded_semantic_ir,
    )
    exploration.transformed_semantic_ir = normalized_pipeline.semantic_ir
    state = Managed3DPageSliderState(
        figure=figure,
        axes=axes_3d,
        pipeline=normalized_pipeline,
        current_scene=cast("LayoutScene3D", pipeline.paged_scene),
        horizontal_slider=None,
        horizontal_axes=slider_axes,
        start_column=0,
        window_size=window_size,
        max_start_column=max_start_column,
        scene_cache={},
        ui_palette=palette,
        exploration=exploration,
        keyboard_shortcuts_enabled=keyboard_shortcuts_enabled,
        double_click_toggle_enabled=double_click_toggle_enabled,
    )
    initial_scene = state._scene_for_start_column(0)
    state.current_scene = initial_scene

    slider = Slider(
        ax=slider_axes,
        label="",
        valmin=0.0,
        valmax=float(max_start_column),
        valinit=0.0,
        valstep=1.0,
        color=palette.slider_fill_color,
        track_color=palette.slider_track_color,
        handle_style={
            "facecolor": palette.accent_color,
            "edgecolor": palette.accent_edgecolor,
            "size": 16,
        },
    )
    _style_slider(slider, palette=palette)
    slider.on_changed(lambda value: state.show_start_column(round(float(value))))
    state.horizontal_slider = slider
    _attach_3d_slider_selection_clicks(state)
    _attach_3d_slider_key_shortcuts(state)
    _ensure_3d_slider_exploration_controls(state)
    _sync_3d_slider_exploration_buttons(state)
    set_page_slider(figure, state)
    return state


def page_slider_window_size(circuit: CircuitIR, style: DrawStyle) -> int:
    """Return the number of columns that fit in the first 2D page budget."""

    normalized_circuit = normalized_draw_circuit(circuit)
    paging_inputs = build_layout_paging_inputs(normalized_circuit, style)
    metrics = paged_scene_metrics_for_width(
        paging_inputs,
        max_page_width=float(getattr(style, "max_page_width")),
    )
    if not metrics.pages:
        return max(1, len(normalized_circuit.layers))
    first_page = metrics.pages[0]
    return max(1, first_page.end_column - first_page.start_column + 1)


def circuit_window(
    circuit: CircuitIR,
    *,
    start_column: int,
    window_size: int,
) -> CircuitIR:
    """Return a new circuit containing only one contiguous layer window."""

    end_column = min(len(circuit.layers), start_column + window_size)
    return CircuitIR(
        quantum_wires=circuit.quantum_wires,
        classical_wires=circuit.classical_wires,
        layers=tuple(circuit.layers[start_column:end_column]),
        name=circuit.name,
        metadata=dict(circuit.metadata),
    )


def _refresh_3d_slider_exploration_context(state: Managed3DPageSliderState) -> None:
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
    state.pipeline = replace(
        state.pipeline,
        ir=normalized_draw_circuit(lower_semantic_circuit(transformed.semantic_ir)),
    )
    state.scene_cache.clear()
    _refresh_3d_slider_window_metrics(state)


def _refresh_3d_slider_window_metrics(state: Managed3DPageSliderState) -> None:
    from .page_window_3d_ranges import windowed_3d_page_ranges

    page_ranges = windowed_3d_page_ranges(
        state.pipeline,
        figure_size=_figure_size_inches(state.figure),
        axes_bounds=managed_3d_axes_bounds(has_page_slider=True),
    )
    first_page_start, first_page_end = page_ranges[0]
    state.window_size = max(1, first_page_end - first_page_start + 1)
    state.max_start_column = max(0, len(state.pipeline.ir.layers) - state.window_size)
    state.start_column = min(state.start_column, state.max_start_column)
    if state.horizontal_slider is not None:
        state.horizontal_slider.valmax = float(state.max_start_column)


def _attach_3d_slider_selection_clicks(state: Managed3DPageSliderState) -> None:
    canvas = getattr(state.figure, "canvas", None)
    if canvas is None:
        return
    if state.click_press_callback_id is not None:
        canvas.mpl_disconnect(state.click_press_callback_id)
    if state.click_release_callback_id is not None:
        canvas.mpl_disconnect(state.click_release_callback_id)

    def _handle_press(event: MouseEvent) -> None:
        if state.exploration is None or event.inaxes is not state.axes or event.button != 1:
            state.pending_click = None
            return
        state.pending_click = (float(event.x), float(event.y), bool(event.dblclick))

    def _handle_release(event: MouseEvent) -> None:
        if state.exploration is None:
            return
        pending_click = state.pending_click
        state.pending_click = None
        if (
            pending_click is None
            or event.inaxes is not state.axes
            or event.button != 1
            or ((float(event.x) - pending_click[0]) ** 2 + (float(event.y) - pending_click[1]) ** 2)
            ** 0.5
            > _CLICK_RELEASE_MAX_DRAG_PIXELS
        ):
            return
        operation_id = clicked_artist_operation_id(cast("Axes", state.axes), event)
        if state.double_click_toggle_enabled and pending_click[2]:
            toggle_operation_with_selection(state, operation_id)
            return
        state.select_operation(operation_id)

    state.click_press_callback_id = int(canvas.mpl_connect("button_press_event", _handle_press))
    state.click_release_callback_id = int(
        canvas.mpl_connect("button_release_event", _handle_release)
    )


def _attach_3d_slider_key_shortcuts(state: Managed3DPageSliderState) -> None:
    canvas = getattr(state.figure, "canvas", None)
    if canvas is None:
        return
    if state.key_callback_id is not None:
        canvas.mpl_disconnect(state.key_callback_id)

    def _handle_key(event: KeyEvent) -> None:
        if not state.keyboard_shortcuts_enabled:
            return
        key_name = managed_key_name(event)
        if key_name == "left":
            state.step_start_column(-1)
            return
        if key_name == "right":
            state.step_start_column(1)
            return
        if is_block_toggle_key(event):
            state.toggle_selected_block()

    state.key_callback_id = int(canvas.mpl_connect("key_press_event", _handle_key))


def _3d_slider_exploration_button_bounds(
    state: Managed3DPageSliderState,
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


def _ensure_3d_slider_exploration_controls(state: Managed3DPageSliderState) -> None:
    from matplotlib.widgets import Button

    if state.ui_palette is None:
        return

    desired_bounds = _3d_slider_exploration_button_bounds(state)
    desired_presence = {
        "wire_filter": "wire_filter" in desired_bounds,
        "ancilla": "ancilla" in desired_bounds,
        "block": "block" in desired_bounds,
    }
    current_presence = {
        "wire_filter": state.wire_filter_button is not None and state.wire_filter_axes is not None,
        "ancilla": state.ancilla_toggle_button is not None
        and state.ancilla_toggle_axes is not None,
        "block": state.block_toggle_button is not None and state.block_toggle_axes is not None,
    }
    if current_presence != desired_presence:
        _remove_3d_slider_exploration_controls(state)

    if desired_presence["wire_filter"] and state.wire_filter_axes is None:
        wire_filter_axes = state.figure.add_axes(
            desired_bounds["wire_filter"],
            facecolor=state.ui_palette.surface_facecolor,
        )
        wire_filter_axes.set_zorder(_OPTIONAL_BUTTON_ZORDER)
        _style_control_axes(wire_filter_axes, palette=state.ui_palette)
        wire_filter_button = Button(
            wire_filter_axes,
            "",
            color=state.ui_palette.surface_facecolor,
            hovercolor=state.ui_palette.surface_hover_facecolor,
        )
        _style_stepper_button(wire_filter_button, palette=state.ui_palette)
        wire_filter_button.on_clicked(lambda _: state.toggle_wire_filter())
        state.wire_filter_axes = wire_filter_axes
        state.wire_filter_button = wire_filter_button
    elif state.wire_filter_axes is not None:
        state.wire_filter_axes.set_position(desired_bounds["wire_filter"])

    if desired_presence["ancilla"] and state.ancilla_toggle_axes is None:
        ancilla_toggle_axes = state.figure.add_axes(
            desired_bounds["ancilla"],
            facecolor=state.ui_palette.surface_facecolor,
        )
        ancilla_toggle_axes.set_zorder(_OPTIONAL_BUTTON_ZORDER)
        _style_control_axes(ancilla_toggle_axes, palette=state.ui_palette)
        ancilla_toggle_button = Button(
            ancilla_toggle_axes,
            "",
            color=state.ui_palette.surface_facecolor,
            hovercolor=state.ui_palette.surface_hover_facecolor,
        )
        _style_stepper_button(ancilla_toggle_button, palette=state.ui_palette)
        ancilla_toggle_button.on_clicked(lambda _: state.toggle_ancillas())
        state.ancilla_toggle_axes = ancilla_toggle_axes
        state.ancilla_toggle_button = ancilla_toggle_button
    elif state.ancilla_toggle_axes is not None:
        state.ancilla_toggle_axes.set_position(desired_bounds["ancilla"])

    if desired_presence["block"] and state.block_toggle_axes is None:
        block_toggle_axes = state.figure.add_axes(
            desired_bounds["block"],
            facecolor=state.ui_palette.surface_facecolor,
        )
        block_toggle_axes.set_zorder(_OPTIONAL_BUTTON_ZORDER)
        _style_control_axes(block_toggle_axes, palette=state.ui_palette)
        block_toggle_button = Button(
            block_toggle_axes,
            "",
            color=state.ui_palette.surface_facecolor,
            hovercolor=state.ui_palette.surface_hover_facecolor,
        )
        _style_stepper_button(block_toggle_button, palette=state.ui_palette)
        block_toggle_button.on_clicked(lambda _: state.toggle_selected_block())
        state.block_toggle_axes = block_toggle_axes
        state.block_toggle_button = block_toggle_button
    elif state.block_toggle_axes is not None:
        state.block_toggle_axes.set_position(desired_bounds["block"])


def _remove_3d_slider_exploration_controls(state: Managed3DPageSliderState) -> None:
    for widget in (
        state.wire_filter_button,
        state.ancilla_toggle_button,
        state.block_toggle_button,
    ):
        if widget is not None and hasattr(widget, "disconnect_events"):
            widget.disconnect_events()

    for axes in (
        state.wire_filter_axes,
        state.ancilla_toggle_axes,
        state.block_toggle_axes,
    ):
        if axes is not None:
            axes.remove()

    state.wire_filter_button = None
    state.ancilla_toggle_button = None
    state.block_toggle_button = None
    state.wire_filter_axes = None
    state.ancilla_toggle_axes = None
    state.block_toggle_axes = None


def _sync_3d_slider_exploration_buttons(state: Managed3DPageSliderState) -> None:
    if state.ui_palette is None or state.exploration is None:
        return

    if state.wire_filter_button is not None:
        state.wire_filter_button.label.set_text(
            "Wires: Active"
            if state.exploration.wire_filter_mode is WireFilterMode.ACTIVE
            else "Wires: All"
        )
        state.wire_filter_button.label.set_fontsize(8.8)

    if state.ancilla_toggle_button is not None:
        state.ancilla_toggle_button.label.set_text(
            "Ancillas: Show" if state.exploration.show_ancillas else "Ancillas: Hide"
        )
        state.ancilla_toggle_button.label.set_fontsize(8.2)

    block_action = selected_block_action(
        state.exploration.catalog,
        selected_operation_id=state.exploration.selected_operation_id,
        collapsed_block_ids=state.exploration.collapsed_block_ids,
    )
    if state.block_toggle_button is not None:
        state.block_toggle_button.label.set_text("" if block_action is None else block_action.label)
        state.block_toggle_button.label.set_fontsize(8.2)
