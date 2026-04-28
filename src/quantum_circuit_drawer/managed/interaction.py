"""Shared helpers for managed Matplotlib keyboard and double-click interactions."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Protocol, cast

from matplotlib.backend_bases import FigureCanvasBase, KeyEvent

from .exploration_2d import ExplorationCatalog, selected_block_action


class _SelectableToggleableState(Protocol):
    def select_operation(self, operation_id: str | None) -> None:
        """Select one semantic operation or clear the selection."""

    def toggle_selected_block(self) -> None:
        """Toggle the currently selected semantic block."""


_MANAGED_KEY_ALIASES: dict[str, str] = {
    "iso_left_tab": "shift+tab",
    "ctrl+iso_left_tab": "ctrl+shift+tab",
    "control+iso_left_tab": "ctrl+shift+tab",
    "control+tab": "ctrl+tab",
    "control+shift+tab": "ctrl+shift+tab",
}
_MANAGED_TAB_BINDINGS_INSTALLED_ATTR = (
    "_quantum_circuit_drawer_managed_tab_focus_bindings_installed"
)


def managed_key_name(event: KeyEvent) -> str:
    """Return a normalized Matplotlib key name."""

    key_name = "" if event.key is None else str(event.key).lower()
    return _MANAGED_KEY_ALIASES.get(key_name, key_name)


def restore_managed_canvas_focus(canvas: object | None) -> None:
    """Best-effort return keyboard focus to one managed Matplotlib canvas."""

    if canvas is None:
        return

    tk_widget_getter = getattr(canvas, "get_tk_widget", None)
    if callable(tk_widget_getter):
        try:
            tk_widget = tk_widget_getter()
        except Exception:
            tk_widget = None
        focus_set = getattr(tk_widget, "focus_set", None)
        if callable(focus_set):
            try:
                focus_set()
                return
            except Exception:
                pass

    for focus_method_name in ("setFocus", "SetFocus", "focus_set"):
        focus_method = getattr(canvas, focus_method_name, None)
        if not callable(focus_method):
            continue
        try:
            focus_method()
            return
        except TypeError:
            continue
        except Exception:
            return


def install_managed_tab_focus_bindings(canvas: object | None) -> None:
    """Install Tk-specific Tab bindings that preserve canvas focus."""

    if canvas is None or bool(getattr(canvas, _MANAGED_TAB_BINDINGS_INSTALLED_ATTR, False)):
        return

    tk_widget_getter = getattr(canvas, "get_tk_widget", None)
    if not callable(tk_widget_getter):
        return

    try:
        tk_widget = tk_widget_getter()
    except Exception:
        return
    bind = getattr(tk_widget, "bind", None)
    if not callable(bind):
        return

    def _forward_tab_key(key_name: str, event: object) -> str:
        dispatch_managed_key_event(canvas, key_name=key_name, gui_event=event)
        restore_managed_canvas_focus(canvas)
        return "break"

    bind("<Tab>", lambda event: _forward_tab_key("tab", event), add="+")
    bind("<Shift-Tab>", lambda event: _forward_tab_key("shift+tab", event), add="+")
    bind("<ISO_Left_Tab>", lambda event: _forward_tab_key("shift+tab", event), add="+")
    bind("<Control-Tab>", lambda event: _forward_tab_key("ctrl+tab", event), add="+")
    bind(
        "<Control-Shift-Tab>",
        lambda event: _forward_tab_key("ctrl+shift+tab", event),
        add="+",
    )
    bind(
        "<Control-ISO_Left_Tab>",
        lambda event: _forward_tab_key("ctrl+shift+tab", event),
        add="+",
    )
    setattr(canvas, _MANAGED_TAB_BINDINGS_INSTALLED_ATTR, True)


def dispatch_managed_key_event(
    canvas: object | None,
    *,
    key_name: str,
    gui_event: object | None = None,
) -> None:
    """Dispatch one synthetic managed key event through Matplotlib callbacks."""

    if canvas is None:
        return
    callbacks = getattr(canvas, "callbacks", None)
    process = getattr(callbacks, "process", None)
    if not callable(process):
        return
    event = KeyEvent(
        "key_press_event",
        cast(FigureCanvasBase, canvas),
        key=key_name,
        guiEvent=gui_event,
    )
    process("key_press_event", event)


def run_managed_canvas_action(canvas: object | None, action: Callable[[], None]) -> None:
    """Run one managed action and then try to keep keyboard focus on the canvas."""

    action()
    restore_managed_canvas_focus(canvas)


def is_block_toggle_key(event: KeyEvent) -> bool:
    """Return whether the key event should toggle the current block selection."""

    return managed_key_name(event) in {"enter", " "}


def is_clear_selection_key(event: KeyEvent) -> bool:
    """Return whether the key event should clear the current selection."""

    return managed_key_name(event) == "escape"


def is_next_selection_key(event: KeyEvent) -> bool:
    """Return whether the key event should move to the next expandable selection."""

    return managed_key_name(event) == "tab"


def is_previous_selection_key(event: KeyEvent) -> bool:
    """Return whether the key event should move to the previous expandable selection."""

    return managed_key_name(event) == "shift+tab"


def is_next_column_key(event: KeyEvent) -> bool:
    """Return whether the key event should move to the next visible column."""

    return managed_key_name(event) == "ctrl+tab"


def is_previous_column_key(event: KeyEvent) -> bool:
    """Return whether the key event should move to the previous visible column."""

    return managed_key_name(event) == "ctrl+shift+tab"


def is_reset_view_key(event: KeyEvent) -> bool:
    """Return whether the key event should restore the original managed view."""

    return managed_key_name(event) == "0"


def is_cycle_topology_key(event: KeyEvent) -> bool:
    """Return whether the key event should cycle the active 3D topology."""

    return managed_key_name(event) == "t" and not is_previous_topology_key(event)


def is_previous_topology_key(event: KeyEvent) -> bool:
    """Return whether the key event should cycle to the previous 3D topology."""

    raw_key_name = "" if event.key is None else str(event.key)
    return raw_key_name == "T" or managed_key_name(event) == "shift+t"


def is_toggle_wire_filter_key(event: KeyEvent) -> bool:
    """Return whether the key event should toggle the wire filter mode."""

    return managed_key_name(event) == "w"


def is_shortcut_help_key(event: KeyEvent) -> bool:
    """Return whether the key event should toggle the shortcut-help overlay."""

    return managed_key_name(event) in {"?", "shift+/"}


def is_home_key(event: KeyEvent) -> bool:
    """Return whether the key event should jump to the absolute start."""

    return managed_key_name(event) == "home"


def is_end_key(event: KeyEvent) -> bool:
    """Return whether the key event should jump to the absolute end."""

    return managed_key_name(event) == "end"


def is_page_up_key(event: KeyEvent) -> bool:
    """Return whether the key event should trigger a large backward step."""

    return managed_key_name(event) == "pageup"


def is_page_down_key(event: KeyEvent) -> bool:
    """Return whether the key event should trigger a large forward step."""

    return managed_key_name(event) == "pagedown"


def is_plus_key(event: KeyEvent) -> bool:
    """Return whether the key event should increase a visible-count control."""

    return managed_key_name(event) in {"+", "plus"}


def is_minus_key(event: KeyEvent) -> bool:
    """Return whether the key event should decrease a visible-count control."""

    return managed_key_name(event) in {"-", "minus"}


def managed_text_boxes_capture_keys(text_boxes: Iterable[object | None]) -> bool:
    """Return whether any managed TextBox is currently capturing keyboard input."""

    return any(bool(getattr(text_box, "capturekeystrokes", False)) for text_box in text_boxes)


def toggle_operation_with_selection(
    state: _SelectableToggleableState,
    operation_id: str | None,
) -> None:
    """Select an operation and toggle its owning block when possible."""

    if operation_id is None:
        return
    state.select_operation(operation_id)
    state.toggle_selected_block()


def visible_expandable_operation_ids(
    operation_items: Iterable[object],
    *,
    catalog: ExplorationCatalog,
    collapsed_block_ids: set[str] | frozenset[str],
) -> tuple[str, ...]:
    """Return visible operation ids that can expand or collapse in visual order."""

    operation_ids: list[str] = []
    seen_block_ids: set[str] = set()
    for item in operation_items:
        operation_id = getattr(item, "operation_id", None)
        if not isinstance(operation_id, str):
            continue
        block_action = selected_block_action(
            catalog,
            selected_operation_id=operation_id,
            collapsed_block_ids=collapsed_block_ids,
        )
        if block_action is None or block_action.block_id in seen_block_ids:
            continue
        seen_block_ids.add(block_action.block_id)
        operation_ids.append(operation_id)
    return tuple(operation_ids)


def visible_operation_ids(operation_items: Iterable[object]) -> tuple[str, ...]:
    """Return visible operation ids in visual order without repeating the same item."""

    operation_ids: list[str] = []
    seen_operation_ids: set[str] = set()
    for item in operation_items:
        operation_id = getattr(item, "operation_id", None)
        if not isinstance(operation_id, str) or operation_id in seen_operation_ids:
            continue
        seen_operation_ids.add(operation_id)
        operation_ids.append(operation_id)
    return tuple(operation_ids)


def visible_column_operation_ids(operation_items: Iterable[object]) -> tuple[str, ...]:
    """Return one visible operation id per visual column in left-to-right order."""

    return tuple(operation_id for _, operation_id in _visible_column_entries(operation_items))


def visible_operation_ids_in_tab_order(operation_items: Iterable[object]) -> tuple[str, ...]:
    """Return visible operation ids ordered by column and then by visual row."""

    operation_entries: list[tuple[int, float, int, str]] = []
    seen_operation_ids: set[str] = set()
    for index, item in enumerate(operation_items):
        operation_id = getattr(item, "operation_id", None)
        column = getattr(item, "column", None)
        if (
            not isinstance(operation_id, str)
            or not operation_id
            or not isinstance(column, int)
            or operation_id in seen_operation_ids
        ):
            continue
        seen_operation_ids.add(operation_id)
        operation_entries.append((column, _tab_order_row_coordinate(item), index, operation_id))
    operation_entries.sort(key=lambda entry: (entry[0], entry[1], entry[2], entry[3]))
    return tuple(operation_id for _, _, _, operation_id in operation_entries)


def _visible_column_entries(operation_items: Iterable[object]) -> tuple[tuple[int, str], ...]:
    operation_entries: list[tuple[int, float, int, str]] = []
    seen_operation_ids: set[str] = set()
    for index, item in enumerate(operation_items):
        operation_id = getattr(item, "operation_id", None)
        column = getattr(item, "column", None)
        if (
            not isinstance(operation_id, str)
            or not operation_id
            or not isinstance(column, int)
            or operation_id in seen_operation_ids
        ):
            continue
        seen_operation_ids.add(operation_id)
        operation_entries.append((column, _tab_order_row_coordinate(item), index, operation_id))
    operation_entries.sort(key=lambda entry: (entry[0], entry[1], entry[2], entry[3]))

    visible_columns: list[tuple[int, str]] = []
    seen_columns: set[int] = set()
    for column, _, _, operation_id in operation_entries:
        if column in seen_columns:
            continue
        seen_columns.add(column)
        visible_columns.append((column, operation_id))
    return tuple(visible_columns)


def _operation_column(
    operation_items: Iterable[object],
    current_operation_id: str | None,
) -> int | None:
    if current_operation_id is None:
        return None
    for item in operation_items:
        operation_id = getattr(item, "operation_id", None)
        column = getattr(item, "column", None)
        if operation_id == current_operation_id and isinstance(column, int):
            return column
    return None


def _tab_order_row_coordinate(item: object) -> float:
    y_coordinate = getattr(item, "y", None)
    if isinstance(y_coordinate, int | float):
        return float(y_coordinate)

    quantum_y = getattr(item, "quantum_y", None)
    if isinstance(quantum_y, int | float):
        return float(quantum_y)

    y_top = getattr(item, "y_top", None)
    if isinstance(y_top, int | float):
        return float(y_top)

    center = getattr(item, "center", None)
    center_x = getattr(center, "x", None)
    if isinstance(center_x, int | float):
        return float(center_x)

    x_coordinate = getattr(item, "x", None)
    if isinstance(x_coordinate, int | float):
        return float(x_coordinate)

    return 0.0


def next_visible_operation_selection(
    visible_operation_ids: Sequence[str],
    current_operation_id: str | None,
    *,
    backwards: bool = False,
    wrap: bool = True,
) -> str | None:
    """Return the next visible operation using visual traversal."""

    if not visible_operation_ids:
        return None
    if current_operation_id not in visible_operation_ids:
        return visible_operation_ids[-1] if backwards else visible_operation_ids[0]
    current_index = visible_operation_ids.index(current_operation_id)
    step = -1 if backwards else 1
    next_index = current_index + step
    if 0 <= next_index < len(visible_operation_ids):
        return visible_operation_ids[next_index]
    if wrap:
        return visible_operation_ids[next_index % len(visible_operation_ids)]
    return None


def next_visible_column_selection(
    operation_items: Iterable[object],
    current_operation_id: str | None,
    *,
    backwards: bool = False,
    wrap: bool = True,
) -> str | None:
    """Return the representative operation for the next visible column."""

    column_entries = _visible_column_entries(operation_items)
    if not column_entries:
        return None

    visible_columns = tuple(column for column, _ in column_entries)
    visible_operation_ids = tuple(operation_id for _, operation_id in column_entries)
    current_column = _operation_column(operation_items, current_operation_id)
    if current_column not in visible_columns:
        return visible_operation_ids[-1] if backwards else visible_operation_ids[0]

    current_index = visible_columns.index(current_column)
    step = -1 if backwards else 1
    next_index = current_index + step
    if 0 <= next_index < len(visible_operation_ids):
        return visible_operation_ids[next_index]
    if wrap:
        return visible_operation_ids[next_index % len(visible_operation_ids)]
    return None


__all__ = [
    "dispatch_managed_key_event",
    "is_block_toggle_key",
    "is_cycle_topology_key",
    "is_clear_selection_key",
    "is_end_key",
    "is_home_key",
    "is_minus_key",
    "is_next_column_key",
    "is_next_selection_key",
    "is_page_down_key",
    "is_page_up_key",
    "is_plus_key",
    "is_previous_column_key",
    "is_previous_topology_key",
    "is_previous_selection_key",
    "is_reset_view_key",
    "is_shortcut_help_key",
    "is_toggle_wire_filter_key",
    "install_managed_tab_focus_bindings",
    "managed_key_name",
    "managed_text_boxes_capture_keys",
    "next_visible_column_selection",
    "next_visible_operation_selection",
    "restore_managed_canvas_focus",
    "run_managed_canvas_action",
    "toggle_operation_with_selection",
    "visible_column_operation_ids",
    "visible_operation_ids_in_tab_order",
    "visible_operation_ids",
    "visible_expandable_operation_ids",
]
