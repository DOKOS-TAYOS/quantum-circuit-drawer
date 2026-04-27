"""Shared helpers for managed Matplotlib keyboard and double-click interactions."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from matplotlib.backend_bases import KeyEvent


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


__all__ = [
    "is_block_toggle_key",
    "managed_key_name",
    "managed_text_boxes_capture_keys",
    "toggle_operation_with_selection",
]
