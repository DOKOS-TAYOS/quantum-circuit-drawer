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
