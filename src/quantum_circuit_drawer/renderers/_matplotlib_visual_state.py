"""Shared visual-state styling helpers for interactive 2D scene elements."""

from __future__ import annotations

from ..layout.scene import SceneVisualState
from ..style.theme import DrawTheme


def alpha_for_visual_state(visual_state: SceneVisualState) -> float:
    """Return the alpha multiplier for one scene visual state."""

    if visual_state is SceneVisualState.DIMMED:
        return 0.2
    if visual_state is SceneVisualState.RELATED:
        return 0.74
    return 1.0


def line_width_scale_for_visual_state(visual_state: SceneVisualState) -> float:
    """Return the line-width multiplier for one scene visual state."""

    if visual_state is SceneVisualState.HIGHLIGHTED:
        return 1.5
    if visual_state is SceneVisualState.RELATED:
        return 1.1
    return 1.0


def color_for_visual_state(
    base_color: str,
    *,
    theme: DrawTheme,
    visual_state: SceneVisualState,
) -> str:
    """Return the effective line or text color for one scene visual state."""

    if visual_state in {SceneVisualState.HIGHLIGHTED, SceneVisualState.RELATED}:
        return theme.accent_color
    return base_color


def gate_facecolor_for_visual_state(
    *,
    theme: DrawTheme,
    visual_state: SceneVisualState,
) -> str:
    """Return the effective gate facecolor for one scene visual state."""

    if visual_state is SceneVisualState.HIGHLIGHTED:
        return theme.measurement_facecolor
    if visual_state is SceneVisualState.RELATED:
        return theme.ui_surface_hover_facecolor or theme.measurement_facecolor
    return theme.gate_facecolor


def measurement_facecolor_for_visual_state(
    *,
    theme: DrawTheme,
    visual_state: SceneVisualState,
) -> str:
    """Return the effective measurement facecolor for one scene visual state."""

    if visual_state in {SceneVisualState.HIGHLIGHTED, SceneVisualState.RELATED}:
        return theme.ui_surface_hover_facecolor or theme.measurement_facecolor
    return theme.measurement_facecolor
