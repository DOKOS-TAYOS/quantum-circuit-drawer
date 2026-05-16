"""Small helpers for notebook display hooks."""

from __future__ import annotations

from collections.abc import Iterable
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def display_figures_in_ipython(
    figures: Iterable[Figure],
    *,
    close_after_display: bool,
) -> None:
    """Display Matplotlib figures through IPython without emitting result reprs."""

    materialized_figures = tuple(figures)
    if not materialized_figures:
        return
    try:
        ipython_display_module = import_module("IPython.display")
        display = getattr(ipython_display_module, "display", None)
    except Exception:
        return
    if not callable(display):
        return

    for figure in materialized_figures:
        target = _ipython_display_target(figure)
        if target is getattr(figure, "canvas", None):
            _display_widget_background_css(ipython_display_module, figure)
        display(target)
        if target is getattr(figure, "canvas", None):
            _suppress_pending_widget_auto_display(figure)
    if close_after_display:
        close_figures_in_pyplot(materialized_figures)


def _ipython_display_target(figure: Figure) -> object:
    """Return the richest IPython display object for a Matplotlib figure."""

    canvas = getattr(figure, "canvas", None)
    if canvas is not None and _has_ipython_rich_display(canvas):
        return canvas
    return figure


def _has_ipython_rich_display(value: object) -> bool:
    return any(
        callable(getattr(value, attr, None))
        for attr in ("_ipython_display_", "_repr_mimebundle_", "_repr_html_")
    )


def _display_widget_background_css(ipython_display_module: object, figure: Figure) -> None:
    from matplotlib.colors import to_hex

    html_factory = getattr(ipython_display_module, "HTML", None)
    display = getattr(ipython_display_module, "display", None)
    if not callable(html_factory) or not callable(display):
        return

    background = to_hex(figure.patch.get_facecolor(), keep_alpha=False)
    text_color = "#f8fafc" if _is_dark_hex_color(background) else "#111827"
    display(
        html_factory(
            f"""
<style>
.jupyter-matplotlib,
.jupyter-matplotlib-header,
.jupyter-matplotlib-footer {{
    background-color: {background} !important;
    color: {text_color} !important;
}}
</style>
"""
        )
    )


def _is_dark_hex_color(color: str) -> bool:
    red = int(color[1:3], 16) / 255.0
    green = int(color[3:5], 16) / 255.0
    blue = int(color[5:7], 16) / 255.0
    return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue) < 0.5


def _suppress_pending_widget_auto_display(figure: Figure) -> None:
    try:
        backend_nbagg = import_module("ipympl.backend_nbagg")
    except Exception:
        return

    backend = getattr(backend_nbagg, "_Backend_ipympl", None)
    pending_figures = getattr(backend, "_to_show", None)
    if not isinstance(pending_figures, list):
        return
    while figure in pending_figures:
        pending_figures.remove(figure)
    if not pending_figures and hasattr(backend, "_draw_called"):
        backend._draw_called = False


def close_figures_in_pyplot(figures: Iterable[Figure]) -> None:
    """Close figures best-effort so notebook inline backends do not auto-repeat them."""

    materialized_figures = tuple(figures)
    if not materialized_figures:
        return
    try:
        from matplotlib import pyplot as plt
    except Exception:
        return

    for figure in materialized_figures:
        try:
            plt.close(figure)
        except Exception:
            continue
