"""Default values for the public drawing style configuration."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from numbers import Real
from typing import TypedDict, Unpack

from .theme import DrawTheme, resolve_theme

DEFAULT_LINE_WIDTH = 1.6


class DrawStyleChanges(TypedDict, total=False):
    font_size: float
    wire_spacing: float
    layer_spacing: float
    gate_width: float
    gate_height: float
    line_width: float | None
    control_radius: float
    show_params: bool
    show_wire_labels: bool
    use_mathtext: bool
    theme: DrawTheme
    margin_left: float
    margin_right: float
    margin_top: float
    margin_bottom: float
    label_margin: float
    classical_wire_gap: float
    swap_marker_size: float
    max_page_width: float
    page_vertical_gap: float


@dataclass(slots=True)
class DrawStyle:
    """Typed style configuration accepted by ``style=...``.

    ``DrawStyle`` mirrors the user-facing style options documented for the
    public API. Instances are typically passed directly or produced by
    ``normalize_style(...)`` after validating a mapping.
    """

    font_size: float = 12.0
    wire_spacing: float = 1.2
    layer_spacing: float = 0.45
    gate_width: float = 0.72
    gate_height: float = 0.72
    line_width: float | None = None
    control_radius: float = 0.08
    show_params: bool = True
    show_wire_labels: bool = True
    use_mathtext: bool = True
    theme: DrawTheme = field(default_factory=lambda: resolve_theme(None))
    margin_left: float = 0.85
    margin_right: float = 0.35
    margin_top: float = 0.8
    margin_bottom: float = 0.8
    label_margin: float = 0.18
    classical_wire_gap: float = 0.75
    swap_marker_size: float = 0.14
    max_page_width: float = 20.0
    page_vertical_gap: float = 1.8
    _line_width_is_default: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.line_width is None:
            self.line_width = DEFAULT_LINE_WIDTH
            self._line_width_is_default = True
            return
        self._line_width_is_default = False


def replace_draw_style(style: DrawStyle, /, **changes: Unpack[DrawStyleChanges]) -> DrawStyle:
    """Return a ``DrawStyle`` replacement while preserving line-width provenance."""

    if "line_width" in changes:
        line_width_change = changes["line_width"]
    else:
        line_width_change = style.line_width
    if line_width_change is None:
        changes["line_width"] = DEFAULT_LINE_WIDTH
        line_width_is_default = True
    elif not isinstance(line_width_change, Real) or float(line_width_change) <= 0.0:
        raise ValueError("line_width must be a positive number")
    else:
        line_width_is_default = False if "line_width" in changes else style._line_width_is_default

    replaced_style = replace(style, **changes)
    replaced_style._line_width_is_default = line_width_is_default
    return replaced_style


def uses_default_line_width(style: DrawStyle) -> bool:
    """Return whether ``style.line_width`` still comes from the library default."""

    return style._line_width_is_default


def resolved_line_width(style: DrawStyle) -> float:
    """Return a non-optional validated line width."""

    line_width = style.line_width
    assert line_width is not None
    return float(line_width)
