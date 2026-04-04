"""Style parsing and validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, replace

from ..exceptions import StyleValidationError
from .defaults import DrawStyle
from .theme import resolve_theme

STYLE_KEYS = set(DrawStyle.__dataclass_fields__.keys())
POSITIVE_FIELDS = {
    "font_size",
    "wire_spacing",
    "layer_spacing",
    "gate_width",
    "gate_height",
    "line_width",
    "control_radius",
    "margin_left",
    "margin_right",
    "margin_top",
    "margin_bottom",
    "label_margin",
    "classical_wire_gap",
    "swap_marker_size",
    "max_page_width",
    "page_vertical_gap",
}
BOOLEAN_FIELDS = {"show_params", "show_wire_labels"}


def normalize_style(style: DrawStyle | Mapping[str, object] | None) -> DrawStyle:
    """Normalize style input into a validated DrawStyle instance."""

    if style is None:
        normalized = DrawStyle()
    elif isinstance(style, DrawStyle):
        normalized = replace(style)
    elif isinstance(style, Mapping):
        unknown = set(style) - STYLE_KEYS
        if unknown:
            keys = ", ".join(sorted(unknown))
            raise StyleValidationError(f"unknown style option(s): {keys}")
        normalized = DrawStyle()
        for field in fields(DrawStyle):
            if field.name not in style:
                continue
            setattr(normalized, field.name, style[field.name])
    else:
        raise StyleValidationError("style must be None, a DrawStyle, or a mapping")

    normalized.theme = resolve_theme(normalized.theme)
    _validate_style_values(normalized)
    return normalized


def _validate_style_values(style: DrawStyle) -> None:
    for field_name in POSITIVE_FIELDS:
        value = getattr(style, field_name)
        if not isinstance(value, (int, float)) or value <= 0:
            raise StyleValidationError(f"{field_name} must be a positive number")
    for field_name in BOOLEAN_FIELDS:
        value = getattr(style, field_name)
        if not isinstance(value, bool):
            raise StyleValidationError(f"{field_name} must be a boolean")
