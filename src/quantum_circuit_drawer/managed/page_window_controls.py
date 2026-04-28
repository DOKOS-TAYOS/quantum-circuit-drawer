"""Managed fixed-page-window controls for 2D rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .exploration_2d import (
    WireFilterMode,
    exploration_control_availability,
    selected_block_action,
)
from .page_window_render import _render_current_window
from .page_window_windowing import _clamp_page_index, _clamp_visible_page_count
from .ui_palette import ManagedUiPalette, managed_ui_palette

if TYPE_CHECKING:
    from matplotlib.widgets import Button

    from .page_window import Managed2DPageWindowState

_MAIN_AXES_BOUNDS = (0.02, 0.18, 0.96, 0.8)
_PREVIOUS_PAGE_BUTTON_BOUNDS = (0.132, 0.05, 0.046, 0.06)
_PAGE_BOX_BOUNDS = (0.182, 0.05, 0.062, 0.06)
_NEXT_PAGE_BUTTON_BOUNDS = (0.248, 0.05, 0.046, 0.06)
_VISIBLE_PAGES_BOX_BOUNDS = (0.46, 0.05, 0.062, 0.06)
_VISIBLE_PAGES_DECREMENT_BOUNDS = (0.53, 0.05, 0.03, 0.028)
_VISIBLE_PAGES_INCREMENT_BOUNDS = (0.53, 0.082, 0.03, 0.028)
_OPTIONAL_CONTROL_BOTTOM = 0.05
_OPTIONAL_CONTROL_HEIGHT = 0.06
_OPTIONAL_CONTROL_RIGHT = 0.98
_OPTIONAL_CONTROL_GAP = 0.008
_WIRE_FILTER_BUTTON_WIDTH = 0.104
_ANCILLA_BUTTON_WIDTH = 0.104
_BLOCK_TOGGLE_BUTTON_WIDTH = 0.172
_PAGE_LABEL_POSITION = (0.075, 0.079)
_PAGE_SUFFIX_POSITION = (0.302, 0.079)
_VISIBLE_LABEL_POSITION = (0.406, 0.079)
_VISIBLE_SUFFIX_POSITION = (0.564, 0.079)
_MAIN_AXES_ZORDER = 3.0
_CONTROL_AXES_ZORDER = 1.0


def _attach_controls(state: Managed2DPageWindowState) -> None:
    from matplotlib.widgets import Button, TextBox

    from .controls import _style_control_axes, _style_stepper_button, _style_text_box

    theme = state.scene.style.theme
    palette = state.ui_palette or managed_ui_palette(theme)
    state.axes.set_position(_MAIN_AXES_BOUNDS)
    state.axes.set_zorder(_MAIN_AXES_ZORDER)

    previous_page_button_axes = state.figure.add_axes(
        _PREVIOUS_PAGE_BUTTON_BOUNDS,
        facecolor=palette.surface_facecolor,
    )
    previous_page_button_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
    page_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
    next_page_button_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
    visible_pages_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
    visible_pages_increment_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
    visible_pages_decrement_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
    _ensure_exploration_controls(state)

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
    if not state.controls_enabled:
        return

    if state.page_suffix_text is not None:
        state.page_suffix_text.set_text(f"/ {state.total_pages}")
    if state.visible_suffix_text is not None:
        state.visible_suffix_text.set_text(f"/ {state.total_pages}")

    _ensure_exploration_controls(state)

    if state.page_box is None or state.visible_pages_box is None:
        _sync_navigation_button_states(state)
        _sync_exploration_buttons(state)
        return

    state.is_syncing_inputs = True
    try:
        state.page_box.set_val(str(state.start_page + 1))
        state.visible_pages_box.set_val(str(state.visible_page_count))
    finally:
        state.is_syncing_inputs = False
    _sync_navigation_button_states(state)
    _sync_exploration_buttons(state)


def _page_window_exploration_button_bounds(
    state: Managed2DPageWindowState,
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


def _ensure_exploration_controls(state: Managed2DPageWindowState) -> None:
    from matplotlib.widgets import Button

    from .controls import _style_control_axes, _style_stepper_button

    if state.ui_palette is None:
        return

    desired_bounds = _page_window_exploration_button_bounds(state)
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
        _remove_exploration_controls(state)

    if desired_presence["wire_filter"] and state.wire_filter_axes is None:
        wire_filter_axes = state.figure.add_axes(
            desired_bounds["wire_filter"],
            facecolor=state.ui_palette.surface_facecolor,
        )
        wire_filter_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
        ancilla_toggle_axes.set_zorder(_CONTROL_AXES_ZORDER)
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
        block_toggle_axes.set_zorder(_CONTROL_AXES_ZORDER)
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


def _remove_exploration_controls(state: Managed2DPageWindowState) -> None:
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


def _sync_exploration_buttons(state: Managed2DPageWindowState) -> None:
    if state.ui_palette is None or state.exploration is None:
        return

    if state.wire_filter_button is not None:
        state.wire_filter_button.label.set_text(
            "Wires: Active"
            if state.exploration.wire_filter_mode is WireFilterMode.ACTIVE
            else "Wires: All"
        )
        state.wire_filter_button.label.set_fontsize(8.8)
        _set_button_enabled(
            state.wire_filter_button,
            enabled=True,
            palette=state.ui_palette,
        )

    if state.ancilla_toggle_button is not None:
        state.ancilla_toggle_button.label.set_text(
            "Ancillas: Show" if state.exploration.show_ancillas else "Ancillas: Hide"
        )
        state.ancilla_toggle_button.label.set_fontsize(8.2)
        _set_button_enabled(
            state.ancilla_toggle_button,
            enabled=True,
            palette=state.ui_palette,
        )

    block_action = selected_block_action(
        state.exploration.catalog,
        selected_operation_id=state.exploration.selected_operation_id,
        collapsed_block_ids=state.exploration.collapsed_block_ids,
    )
    if state.block_toggle_button is not None:
        state.block_toggle_button.label.set_text("" if block_action is None else block_action.label)
        state.block_toggle_button.label.set_fontsize(8.2)
        _set_button_enabled(
            state.block_toggle_button,
            enabled=block_action is not None,
            palette=state.ui_palette,
        )
