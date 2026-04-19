"""Internal managed-UI palette helpers for interactive Matplotlib controls."""

from __future__ import annotations

from dataclasses import dataclass

from .style.theme import DrawTheme


@dataclass(frozen=True, slots=True)
class ManagedUiPalette:
    """Resolved UI colors for managed interactive controls."""

    surface_facecolor: str
    surface_hover_facecolor: str
    surface_facecolor_disabled: str
    surface_edgecolor: str
    surface_edgecolor_active: str
    surface_edgecolor_disabled: str
    text_color: str
    secondary_text_color: str
    disabled_text_color: str
    accent_color: str
    accent_edgecolor: str
    slider_track_color: str
    slider_fill_color: str


def managed_ui_palette(theme: DrawTheme) -> ManagedUiPalette:
    """Return the interactive-control palette for the provided draw theme."""

    return ManagedUiPalette(
        surface_facecolor=theme.ui_surface_facecolor or theme.gate_facecolor,
        surface_hover_facecolor=theme.ui_surface_hover_facecolor or theme.measurement_facecolor,
        surface_facecolor_disabled=theme.ui_surface_facecolor_disabled or theme.axes_facecolor,
        surface_edgecolor=theme.ui_surface_edgecolor or theme.barrier_color,
        surface_edgecolor_active=theme.ui_surface_edgecolor_active or theme.accent_color,
        surface_edgecolor_disabled=theme.ui_surface_edgecolor_disabled or theme.barrier_color,
        text_color=theme.ui_text_color or theme.text_color,
        secondary_text_color=theme.ui_secondary_text_color or theme.classical_wire_color,
        disabled_text_color=theme.ui_disabled_text_color or theme.classical_wire_color,
        accent_color=theme.ui_accent_color or theme.accent_color,
        accent_edgecolor=theme.ui_accent_edgecolor or theme.text_color,
        slider_track_color=theme.ui_slider_track_color or theme.classical_wire_color,
        slider_fill_color=theme.ui_slider_fill_color or theme.accent_color,
    )
