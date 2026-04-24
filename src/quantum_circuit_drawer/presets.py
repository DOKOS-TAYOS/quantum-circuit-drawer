"""Shared user-facing style presets."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from .style import DrawStyle, DrawTheme, normalize_style
from .style.defaults import replace_draw_style
from .style.theme import resolve_theme


class StylePreset(StrEnum):
    """Named presets shared by circuit and histogram APIs."""

    PAPER = "paper"
    NOTEBOOK = "notebook"
    COMPACT = "compact"
    PRESENTATION = "presentation"
    ACCESSIBLE = "accessible"


def normalize_style_preset(value: StylePreset | str | None) -> StylePreset | None:
    """Normalize an optional preset name into ``StylePreset``."""

    if value is None:
        return None
    try:
        return value if isinstance(value, StylePreset) else StylePreset(str(value))
    except ValueError as exc:
        choices = ", ".join(preset.value for preset in StylePreset)
        raise ValueError(f"preset must be one of: {choices}") from exc


def apply_draw_style_preset(
    style: DrawStyle | Mapping[str, object] | None,
    *,
    preset: StylePreset | None,
) -> DrawStyle:
    """Apply a preset baseline before explicit user overrides."""

    if preset is None:
        return normalize_style(style)

    preset_style = _draw_style_for_preset(preset)
    if style is None:
        return preset_style
    if isinstance(style, DrawStyle):
        return normalize_style(style)
    if not isinstance(style, Mapping):
        return normalize_style(style)

    preset_mapping = _draw_style_mapping(preset_style)
    merged_style = {**preset_mapping, **style}
    return normalize_style(merged_style)


def histogram_theme_for_preset(preset: StylePreset | None) -> DrawTheme | None:
    """Return the histogram theme baseline for a preset."""

    if preset is None:
        return None
    if preset is StylePreset.PAPER:
        return resolve_theme("paper")
    if preset is StylePreset.NOTEBOOK:
        return resolve_theme("light")
    if preset is StylePreset.ACCESSIBLE:
        return resolve_theme("accessible")
    return resolve_theme("dark")


def histogram_draw_style_for_preset(preset: StylePreset | None) -> str | None:
    """Return the histogram draw-style baseline name for a preset."""

    if preset is None:
        return None
    if preset is StylePreset.PAPER:
        return "soft"
    if preset is StylePreset.COMPACT:
        return "outline"
    if preset is StylePreset.ACCESSIBLE:
        return "outline"
    if preset is StylePreset.PRESENTATION:
        return "solid"
    return "soft"


def histogram_figsize_for_preset(
    preset: StylePreset | None,
) -> tuple[float, float] | None:
    """Return the histogram figure-size baseline for a preset."""

    if preset is None:
        return None
    if preset is StylePreset.COMPACT:
        return (7.0, 3.8)
    if preset is StylePreset.PRESENTATION:
        return (10.0, 5.6)
    return (8.4, 4.6)


def _draw_style_for_preset(preset: StylePreset) -> DrawStyle:
    base_style = DrawStyle()
    if preset is StylePreset.PAPER:
        return replace_draw_style(
            base_style,
            theme=resolve_theme("paper"),
            font_size=11.5,
            wire_spacing=1.15,
            gate_width=0.76,
            gate_height=0.76,
        )
    if preset is StylePreset.NOTEBOOK:
        return replace_draw_style(
            base_style,
            theme=resolve_theme("light"),
            font_size=12.0,
            wire_spacing=1.25,
            gate_width=0.78,
            gate_height=0.78,
        )
    if preset is StylePreset.COMPACT:
        return replace_draw_style(
            base_style,
            theme=resolve_theme("dark"),
            font_size=10.5,
            wire_spacing=1.0,
            layer_spacing=0.38,
            gate_width=0.66,
            gate_height=0.66,
        )
    if preset is StylePreset.ACCESSIBLE:
        return replace_draw_style(
            base_style,
            theme=resolve_theme("accessible"),
            font_size=12.0,
            wire_spacing=1.25,
            line_width=1.9,
            wire_line_width=2.1,
            classical_wire_line_width=1.8,
            gate_edge_line_width=2.0,
            barrier_line_width=1.8,
            measurement_line_width=2.0,
            connection_line_width=1.9,
            topology_edge_line_width=1.2,
            gate_width=0.80,
            gate_height=0.80,
        )
    return replace_draw_style(
        base_style,
        theme=resolve_theme("dark"),
        font_size=13.5,
        wire_spacing=1.3,
        gate_width=0.84,
        gate_height=0.84,
    )


def _draw_style_mapping(style: DrawStyle) -> dict[str, object]:
    return {
        "font_size": style.font_size,
        "wire_spacing": style.wire_spacing,
        "layer_spacing": style.layer_spacing,
        "gate_width": style.gate_width,
        "gate_height": style.gate_height,
        "line_width": style.line_width,
        "wire_line_width": style.wire_line_width,
        "classical_wire_line_width": style.classical_wire_line_width,
        "gate_edge_line_width": style.gate_edge_line_width,
        "barrier_line_width": style.barrier_line_width,
        "measurement_line_width": style.measurement_line_width,
        "connection_line_width": style.connection_line_width,
        "topology_edge_line_width": style.topology_edge_line_width,
        "control_radius": style.control_radius,
        "show_params": style.show_params,
        "show_wire_labels": style.show_wire_labels,
        "use_mathtext": style.use_mathtext,
        "theme": style.theme,
        "margin_left": style.margin_left,
        "margin_right": style.margin_right,
        "margin_top": style.margin_top,
        "margin_bottom": style.margin_bottom,
        "label_margin": style.label_margin,
        "classical_wire_gap": style.classical_wire_gap,
        "swap_marker_size": style.swap_marker_size,
        "max_page_width": style.max_page_width,
        "page_vertical_gap": style.page_vertical_gap,
    }
