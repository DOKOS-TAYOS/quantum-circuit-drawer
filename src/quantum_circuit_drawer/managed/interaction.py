"""Shared helpers for managed Matplotlib keyboard and double-click interactions."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

from matplotlib.backend_bases import KeyEvent

from .exploration_2d import ExplorationCatalog, selected_block_action


class _SelectableToggleableState(Protocol):
    def select_operation(self, operation_id: str | None) -> None:
        """Select one semantic operation or clear the selection."""

    def toggle_selected_block(self) -> None:
        """Toggle the currently selected semantic block."""


def managed_key_name(event: KeyEvent) -> str:
    """Return a normalized Matplotlib key name."""

    return "" if event.key is None else str(event.key).lower()


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


def is_reset_view_key(event: KeyEvent) -> bool:
    """Return whether the key event should restore the original managed view."""

    return managed_key_name(event) == "0"


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

    operation_ids_by_column: dict[int, str] = {}
    for item in operation_items:
        operation_id = getattr(item, "operation_id", None)
        column = getattr(item, "column", None)
        if (
            not isinstance(operation_id, str)
            or not operation_id
            or not isinstance(column, int)
            or column in operation_ids_by_column
        ):
            continue
        operation_ids_by_column[column] = operation_id
    return tuple(operation_ids_by_column[column] for column in sorted(operation_ids_by_column))


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


__all__ = [
    "is_block_toggle_key",
    "is_clear_selection_key",
    "is_end_key",
    "is_home_key",
    "is_minus_key",
    "is_next_selection_key",
    "is_page_down_key",
    "is_page_up_key",
    "is_plus_key",
    "is_previous_selection_key",
    "is_reset_view_key",
    "is_shortcut_help_key",
    "managed_key_name",
    "managed_text_boxes_capture_keys",
    "next_visible_operation_selection",
    "toggle_operation_with_selection",
    "visible_column_operation_ids",
    "visible_operation_ids",
    "visible_expandable_operation_ids",
]
