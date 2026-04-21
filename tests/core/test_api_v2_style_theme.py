from __future__ import annotations

from quantum_circuit_drawer.managed.ui_palette import managed_ui_palette
from quantum_circuit_drawer.style import (
    DrawTheme,
    normalize_style,
    resolved_barrier_line_width,
    resolved_classical_wire_line_width,
    resolved_connection_line_width,
    resolved_gate_edge_line_width,
    resolved_measurement_line_width,
    resolved_topology_edge_line_width,
    resolved_wire_line_width,
)


def test_normalize_style_accepts_family_line_widths() -> None:
    style = normalize_style(
        {
            "line_width": 1.6,
            "wire_line_width": 2.1,
            "classical_wire_line_width": 1.4,
            "gate_edge_line_width": 1.7,
            "barrier_line_width": 0.9,
            "measurement_line_width": 1.2,
            "connection_line_width": 1.8,
            "topology_edge_line_width": 0.7,
        }
    )

    assert resolved_wire_line_width(style) == 2.1
    assert resolved_classical_wire_line_width(style) == 1.4
    assert resolved_gate_edge_line_width(style) == 1.7
    assert resolved_barrier_line_width(style) == 0.9
    assert resolved_measurement_line_width(style) == 1.2
    assert resolved_connection_line_width(style) == 1.8
    assert resolved_topology_edge_line_width(style) == 0.7


def test_managed_ui_palette_uses_theme_managed_colors() -> None:
    theme = DrawTheme(
        name="custom",
        figure_facecolor="#000000",
        axes_facecolor="#010101",
        wire_color="#020202",
        classical_wire_color="#030303",
        gate_facecolor="#040404",
        gate_edgecolor="#050505",
        measurement_facecolor="#060606",
        text_color="#070707",
        barrier_color="#080808",
        measurement_color="#090909",
        accent_color="#101010",
        ui_surface_facecolor="#111111",
        ui_surface_hover_facecolor="#121212",
        ui_surface_facecolor_disabled="#131313",
        ui_surface_edgecolor="#141414",
        ui_surface_edgecolor_active="#151515",
        ui_surface_edgecolor_disabled="#161616",
        ui_text_color="#171717",
        ui_secondary_text_color="#181818",
        ui_disabled_text_color="#191919",
        ui_accent_color="#202020",
        ui_accent_edgecolor="#212121",
        ui_slider_track_color="#222222",
        ui_slider_fill_color="#232323",
    )

    palette = managed_ui_palette(theme)

    assert palette.surface_facecolor == "#111111"
    assert palette.surface_hover_facecolor == "#121212"
    assert palette.surface_facecolor_disabled == "#131313"
    assert palette.surface_edgecolor == "#141414"
    assert palette.surface_edgecolor_active == "#151515"
    assert palette.surface_edgecolor_disabled == "#161616"
    assert palette.text_color == "#171717"
    assert palette.secondary_text_color == "#181818"
    assert palette.disabled_text_color == "#191919"
    assert palette.accent_color == "#202020"
    assert palette.accent_edgecolor == "#212121"
    assert palette.slider_track_color == "#222222"
    assert palette.slider_fill_color == "#232323"
