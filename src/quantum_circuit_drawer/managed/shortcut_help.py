"""Shared shortcut-help overlay helpers for interactive figures."""

from __future__ import annotations

from collections.abc import Sequence

from matplotlib.figure import Figure
from matplotlib.text import Text

from .ui_palette import ManagedUiPalette

_SHORTCUT_HELP_POSITION = (0.018, 0.975)


def create_shortcut_help_text(
    figure: Figure,
    *,
    palette: ManagedUiPalette,
    lines: Sequence[str],
) -> Text:
    """Create one hidden figure-level shortcut-help overlay."""

    help_text = figure.text(
        _SHORTCUT_HELP_POSITION[0],
        _SHORTCUT_HELP_POSITION[1],
        format_shortcut_help(lines),
        color=palette.text_color,
        ha="left",
        va="top",
        fontsize=8.8,
        linespacing=1.35,
        bbox={
            "boxstyle": "round,pad=0.45",
            "facecolor": palette.surface_facecolor,
            "edgecolor": palette.surface_edgecolor,
            "alpha": 0.97,
        },
        zorder=50.0,
    )
    help_text.set_visible(False)
    return help_text


def format_shortcut_help(lines: Sequence[str]) -> str:
    """Return one user-facing shortcut-help block."""

    return "Shortcuts\n" + "\n".join(_format_shortcut_help_line(line) for line in lines)


def _format_shortcut_help_line(line: str) -> str:
    """Return one shortcut-help line with the shortcut segment emphasized."""

    shortcut, separator, description = line.partition(":")
    if separator == "":
        return line
    return f"$\\mathbf{{{shortcut}}}$:{description}"


def toggle_shortcut_help_text(help_text: Text | None, *, figure: Figure) -> None:
    """Toggle one shortcut-help overlay and redraw the figure."""

    if help_text is None:
        return
    help_text.set_visible(not help_text.get_visible())
    canvas = getattr(figure, "canvas", None)
    if canvas is not None:
        canvas.draw_idle()


__all__ = [
    "ManagedUiPalette",
    "create_shortcut_help_text",
    "format_shortcut_help",
    "toggle_shortcut_help_text",
]
