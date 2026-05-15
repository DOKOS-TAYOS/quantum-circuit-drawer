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
        display = getattr(import_module("IPython.display"), "display", None)
    except Exception:
        return
    if not callable(display):
        return

    for figure in materialized_figures:
        display(figure)
    if close_after_display:
        close_figures_in_pyplot(materialized_figures)


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
