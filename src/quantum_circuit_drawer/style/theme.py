"""Theme definitions."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import StyleValidationError


@dataclass(frozen=True, slots=True)
class DrawTheme:
    """Resolved drawing theme."""

    name: str
    figure_facecolor: str
    axes_facecolor: str
    wire_color: str
    classical_wire_color: str
    gate_facecolor: str
    gate_edgecolor: str
    text_color: str
    barrier_color: str
    measurement_color: str
    accent_color: str


THEMES: dict[str, DrawTheme] = {
    "light": DrawTheme(
        name="light",
        figure_facecolor="#ffffff",
        axes_facecolor="#ffffff",
        wire_color="#1f2933",
        classical_wire_color="#52606d",
        gate_facecolor="#f8fafc",
        gate_edgecolor="#0f172a",
        text_color="#0f172a",
        barrier_color="#94a3b8",
        measurement_color="#0f172a",
        accent_color="#0f766e",
    ),
    "paper": DrawTheme(
        name="paper",
        figure_facecolor="#fffdf7",
        axes_facecolor="#fffdf7",
        wire_color="#2d2a26",
        classical_wire_color="#6b5e52",
        gate_facecolor="#fff7e8",
        gate_edgecolor="#5b4636",
        text_color="#2d2a26",
        barrier_color="#b59b7a",
        measurement_color="#5b4636",
        accent_color="#b45309",
    ),
    "dark": DrawTheme(
        name="dark",
        figure_facecolor="#0b1220",
        axes_facecolor="#0b1220",
        wire_color="#dbe4f0",
        classical_wire_color="#8fa3b8",
        gate_facecolor="#111b2e",
        gate_edgecolor="#dbe4f0",
        text_color="#f8fafc",
        barrier_color="#4b5d78",
        measurement_color="#7dd3fc",
        accent_color="#38bdf8",
    ),
}


def resolve_theme(theme: str | DrawTheme | None) -> DrawTheme:
    """Return a concrete theme object."""

    if isinstance(theme, DrawTheme):
        return theme
    if theme is None:
        return THEMES["light"]
    try:
        return THEMES[theme]
    except KeyError as exc:
        raise StyleValidationError(f"unknown theme '{theme}'") from exc
