"""Style defaults."""

from __future__ import annotations

from dataclasses import dataclass, field

from .theme import DrawTheme, resolve_theme


@dataclass(slots=True)
class DrawStyle:
    """Typed style configuration."""

    font_size: float = 12.0
    wire_spacing: float = 1.2
    layer_spacing: float = 0.45
    gate_width: float = 0.72
    gate_height: float = 0.72
    line_width: float = 1.6
    control_radius: float = 0.08
    show_params: bool = True
    show_wire_labels: bool = True
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
