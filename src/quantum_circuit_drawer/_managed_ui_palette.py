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

    if theme.name == "dark":
        return ManagedUiPalette(
            surface_facecolor="#161d26",
            surface_hover_facecolor="#1b2530",
            surface_facecolor_disabled="#11161d",
            surface_edgecolor="#2a3441",
            surface_edgecolor_active="#6cb6ff",
            surface_edgecolor_disabled="#2a3441",
            text_color="#e6edf3",
            secondary_text_color="#9aa7b7",
            disabled_text_color="#9aa7b7",
            accent_color="#6cb6ff",
            accent_edgecolor="#e6edf3",
            slider_track_color="#2a3441",
            slider_fill_color="#6cb6ff",
        )

    return ManagedUiPalette(
        surface_facecolor=theme.gate_facecolor,
        surface_hover_facecolor=theme.measurement_facecolor,
        surface_facecolor_disabled=theme.axes_facecolor,
        surface_edgecolor=theme.barrier_color,
        surface_edgecolor_active=theme.accent_color,
        surface_edgecolor_disabled=theme.barrier_color,
        text_color=theme.text_color,
        secondary_text_color=theme.classical_wire_color,
        disabled_text_color=theme.classical_wire_color,
        accent_color=theme.accent_color,
        accent_edgecolor=theme.text_color,
        slider_track_color=theme.classical_wire_color,
        slider_fill_color=theme.accent_color,
    )
