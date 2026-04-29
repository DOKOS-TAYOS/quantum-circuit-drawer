"""Shared shortcut-help overlay helpers for interactive figures."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from matplotlib.figure import Figure
from matplotlib.text import Text

from .ui_palette import ManagedUiPalette

_SHORTCUT_HELP_POSITION = (0.018, 0.975)

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.widgets import Button


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


def create_shortcut_help_button(
    figure: Figure,
    *,
    palette: ManagedUiPalette,
    bounds: tuple[float, float, float, float],
    on_click: Callable[[object], None],
    zorder: float = 1.0,
) -> tuple[Axes, Button]:
    """Create one circular-looking help button that toggles the shortcut overlay."""

    from matplotlib.widgets import Button

    button_axes = figure.add_axes(bounds, facecolor="none")
    button_axes.set_zorder(zorder)
    button_axes.set_xticks([])
    button_axes.set_yticks([])
    button_axes.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for spine in button_axes.spines.values():
        spine.set_visible(False)
    help_button = Button(
        button_axes,
        "?",
        color="none",
        hovercolor="none",
    )
    help_button.label.set_color(palette.text_color)
    help_button.label.set_fontweight("bold")
    help_button.label.set_bbox(
        {
            "boxstyle": "circle,pad=0.33",
            "facecolor": palette.surface_facecolor,
            "edgecolor": palette.surface_edgecolor_active,
            "linewidth": 1.1,
            "alpha": 0.98,
        }
    )
    help_button.on_clicked(on_click)
    return button_axes, help_button


__all__ = [
    "ManagedUiPalette",
    "create_shortcut_help_button",
    "create_shortcut_help_text",
    "format_shortcut_help",
    "toggle_shortcut_help_text",
]
