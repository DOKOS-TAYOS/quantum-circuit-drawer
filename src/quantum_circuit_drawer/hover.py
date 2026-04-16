"""Typed hover configuration helpers for interactive circuit inspection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Literal, cast

HoverMatrixMode = Literal["never", "auto", "always"]
_HOVER_ALLOWED_KEYS = {
    "enabled",
    "show_name",
    "show_size",
    "show_qubits",
    "show_matrix",
    "matrix_max_qubits",
}
_BOOLEAN_HOVER_FIELDS = {"enabled", "show_name", "show_size", "show_qubits"}
_VALID_SHOW_MATRIX_VALUES = frozenset({"never", "auto", "always"})


@dataclass(frozen=True, slots=True)
class HoverOptions:
    """Interactive hover settings accepted by the public drawing API."""

    enabled: bool = True
    show_name: bool = True
    show_size: bool = True
    show_qubits: bool = True
    show_matrix: HoverMatrixMode = "auto"
    matrix_max_qubits: int = 2

    def to_mapping(self) -> dict[str, object]:
        """Return the options as a plain mapping."""

        return {
            "enabled": self.enabled,
            "show_name": self.show_name,
            "show_size": self.show_size,
            "show_qubits": self.show_qubits,
            "show_matrix": self.show_matrix,
            "matrix_max_qubits": self.matrix_max_qubits,
        }


def normalize_hover(hover: bool | HoverOptions | Mapping[str, object]) -> HoverOptions:
    """Normalize hover input into a validated ``HoverOptions`` instance."""

    if isinstance(hover, bool):
        return HoverOptions(enabled=hover)
    if isinstance(hover, HoverOptions):
        return replace(hover)
    if not isinstance(hover, Mapping):
        raise ValueError("hover must be a boolean, HoverOptions, or a mapping")

    unknown_keys = set(hover) - _HOVER_ALLOWED_KEYS
    if unknown_keys:
        unknown = ", ".join(sorted(unknown_keys))
        raise ValueError(f"unknown hover option(s): {unknown}")

    resolved = HoverOptions()
    for field_name in _BOOLEAN_HOVER_FIELDS:
        if field_name not in hover:
            continue
        value = hover[field_name]
        if not isinstance(value, bool):
            raise ValueError(f"hover.{field_name} must be a boolean")
        if field_name == "enabled":
            resolved = replace(resolved, enabled=value)
        elif field_name == "show_name":
            resolved = replace(resolved, show_name=value)
        elif field_name == "show_size":
            resolved = replace(resolved, show_size=value)
        else:
            resolved = replace(resolved, show_qubits=value)

    if "show_matrix" in hover:
        value = hover["show_matrix"]
        if not isinstance(value, str) or value not in _VALID_SHOW_MATRIX_VALUES:
            choices = ", ".join(sorted(_VALID_SHOW_MATRIX_VALUES))
            raise ValueError(f"hover.show_matrix must be one of: {choices}")
        resolved = replace(resolved, show_matrix=cast(HoverMatrixMode, value))

    if "matrix_max_qubits" in hover:
        value = hover["matrix_max_qubits"]
        if not isinstance(value, int) or value <= 0:
            raise ValueError("hover.matrix_max_qubits must be a positive integer")
        resolved = replace(resolved, matrix_max_qubits=value)

    return resolved


def disable_hover(hover: HoverOptions) -> HoverOptions:
    """Return a copy of ``hover`` with interactivity disabled."""

    if not hover.enabled:
        return hover
    return replace(hover, enabled=False)
