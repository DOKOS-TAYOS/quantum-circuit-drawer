"""Built-in drawing themes and theme resolution helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import StyleValidationError


@dataclass(frozen=True, slots=True)
class DrawTheme:
    """Resolved theme palette used by the renderer after style normalization."""

    name: str
    figure_facecolor: str
    axes_facecolor: str
    wire_color: str
    classical_wire_color: str
    gate_facecolor: str
    gate_edgecolor: str
    measurement_facecolor: str
    text_color: str
    barrier_color: str
    measurement_color: str
    accent_color: str
    control_color: str = ""
    control_connection_color: str = ""
    topology_edge_color: str = ""
    topology_plane_color: str = ""
    hover_text_color: str = "#ffffff"
    hover_facecolor: str = "#222222"
    hover_edgecolor: str = "#cccccc"
    ui_surface_facecolor: str = ""
    ui_surface_hover_facecolor: str = ""
    ui_surface_facecolor_disabled: str = ""
    ui_surface_edgecolor: str = ""
    ui_surface_edgecolor_active: str = ""
    ui_surface_edgecolor_disabled: str = ""
    ui_text_color: str = ""
    ui_secondary_text_color: str = ""
    ui_disabled_text_color: str = ""
    ui_accent_color: str = ""
    ui_accent_edgecolor: str = ""
    ui_slider_track_color: str = ""
    ui_slider_fill_color: str = ""


THEMES: dict[str, DrawTheme] = {
    "light": DrawTheme(
        name="light",
        figure_facecolor="#ffffff",
        axes_facecolor="#ffffff",
        wire_color="#1f2933",
        classical_wire_color="#52606d",
        gate_facecolor="#f8fafc",
        gate_edgecolor="#0f172a",
        measurement_facecolor="#e2eef9",
        text_color="#0f172a",
        barrier_color="#94a3b8",
        measurement_color="#0f172a",
        accent_color="#0f766e",
        control_color="#0f172a",
        control_connection_color="#0f766e",
        topology_edge_color="#b45309",
        topology_plane_color="#0f766e",
        hover_text_color="#ffffff",
        hover_facecolor="#222222",
        hover_edgecolor="#cccccc",
        ui_surface_facecolor="#f8fafc",
        ui_surface_hover_facecolor="#e2eef9",
        ui_surface_facecolor_disabled="#ffffff",
        ui_surface_edgecolor="#94a3b8",
        ui_surface_edgecolor_active="#0f766e",
        ui_surface_edgecolor_disabled="#94a3b8",
        ui_text_color="#0f172a",
        ui_secondary_text_color="#52606d",
        ui_disabled_text_color="#52606d",
        ui_accent_color="#0f766e",
        ui_accent_edgecolor="#0f172a",
        ui_slider_track_color="#52606d",
        ui_slider_fill_color="#0f766e",
    ),
    "paper": DrawTheme(
        name="paper",
        figure_facecolor="#fffdf7",
        axes_facecolor="#fffdf7",
        wire_color="#2d2a26",
        classical_wire_color="#6b5e52",
        gate_facecolor="#fff7e8",
        gate_edgecolor="#5b4636",
        measurement_facecolor="#f6eddc",
        text_color="#2d2a26",
        barrier_color="#b59b7a",
        measurement_color="#5b4636",
        accent_color="#b45309",
        control_color="#5b4636",
        control_connection_color="#b45309",
        topology_edge_color="#b45309",
        topology_plane_color="#b45309",
        hover_text_color="#ffffff",
        hover_facecolor="#222222",
        hover_edgecolor="#cccccc",
        ui_surface_facecolor="#fff7e8",
        ui_surface_hover_facecolor="#f6eddc",
        ui_surface_facecolor_disabled="#fffdf7",
        ui_surface_edgecolor="#b59b7a",
        ui_surface_edgecolor_active="#b45309",
        ui_surface_edgecolor_disabled="#b59b7a",
        ui_text_color="#2d2a26",
        ui_secondary_text_color="#6b5e52",
        ui_disabled_text_color="#6b5e52",
        ui_accent_color="#b45309",
        ui_accent_edgecolor="#2d2a26",
        ui_slider_track_color="#6b5e52",
        ui_slider_fill_color="#b45309",
    ),
    "dark": DrawTheme(
        name="dark",
        figure_facecolor="#0b0f14",
        axes_facecolor="#11161d",
        wire_color="#c5d1de",
        classical_wire_color="#9aa7b7",
        gate_facecolor="#161d26",
        gate_edgecolor="#c5d1de",
        measurement_facecolor="#162432",
        text_color="#e6edf3",
        barrier_color="#4d5b6a",
        measurement_color="#6cb6ff",
        accent_color="#6cb6ff",
        control_color="#c5d1de",
        control_connection_color="#22c55e",
        topology_edge_color="#facc15",
        topology_plane_color="#22c55e",
        hover_text_color="#ffffff",
        hover_facecolor="#222222",
        hover_edgecolor="#cccccc",
        ui_surface_facecolor="#161d26",
        ui_surface_hover_facecolor="#1b2530",
        ui_surface_facecolor_disabled="#11161d",
        ui_surface_edgecolor="#2a3441",
        ui_surface_edgecolor_active="#6cb6ff",
        ui_surface_edgecolor_disabled="#2a3441",
        ui_text_color="#e6edf3",
        ui_secondary_text_color="#9aa7b7",
        ui_disabled_text_color="#9aa7b7",
        ui_accent_color="#6cb6ff",
        ui_accent_edgecolor="#e6edf3",
        ui_slider_track_color="#2a3441",
        ui_slider_fill_color="#6cb6ff",
    ),
}


def resolve_theme(theme: str | DrawTheme | None) -> DrawTheme:
    """Return a concrete theme object.

    ``None`` selects the default dark theme. Unknown string names raise
    ``StyleValidationError``.
    """

    if isinstance(theme, DrawTheme):
        return theme
    if theme is None:
        return THEMES["dark"]
    try:
        return THEMES[theme]
    except KeyError as exc:
        raise StyleValidationError(f"unknown theme '{theme}'") from exc
