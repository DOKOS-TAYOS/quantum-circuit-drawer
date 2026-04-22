"""Shared Matplotlib helper utilities for example entrypoints."""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def normalize_figsize(value: object) -> tuple[float, float]:
    """Validate one user-provided figure size pair."""

    if not isinstance(value, tuple | list) or len(value) != 2:
        raise SystemExit("--figsize must contain width and height.")

    figure_width = float(value[0])
    figure_height = float(value[1])
    if figure_width <= 0.0 or figure_height <= 0.0:
        raise SystemExit("--figsize values must be positive.")
    return figure_width, figure_height


def set_figure_title(*, figure: object, title: str) -> None:
    """Apply a stable label and best-effort window title to one figure-like object."""

    set_label = getattr(figure, "set_label", None)
    if callable(set_label):
        set_label(title)
    _set_window_title(figure=figure, title=title)


def set_result_figure_titles(*, result: object, saved_label: str) -> None:
    """Apply user-facing titles to every figure exposed by one render result."""

    figures = result_figures(result)
    if not figures:
        return

    total_figures = len(figures)
    for page_index, figure in enumerate(figures, start=1):
        title = (
            saved_label
            if total_figures == 1
            else f"{saved_label} - page {page_index}/{total_figures}"
        )
        set_figure_title(figure=figure, title=title)


def result_figures(result: object) -> tuple[object, ...]:
    """Return every figure-like object exposed by one render result."""

    figures = getattr(result, "figures", None)
    if figures is not None:
        if isinstance(figures, tuple):
            return figures
        if isinstance(figures, list):
            return tuple(figures)
        try:
            return tuple(figures)
        except TypeError:
            return ()

    figure = getattr(result, "figure", None)
    if figure is not None:
        return (figure,)
    return ()


def release_rendered_result(result: object) -> None:
    """Close every Matplotlib figure exposed by one render result."""

    figures = _matplotlib_result_figures(result)
    if not figures:
        return

    from matplotlib import pyplot as plt

    for figure in figures:
        try:
            plt.close(figure)
        except Exception:
            continue
    gc.collect()


def is_destroyed_window_error(error: Exception) -> bool:
    """Return whether one backend error only means the window is already gone."""

    error_name = type(error).__name__
    if error_name not in {"TclError", "RuntimeError"}:
        return False

    normalized_message = str(error).lower()
    destroyed_markers = (
        "application has been destroyed",
        "already deleted",
        "has been deleted",
        "does not exist",
    )
    return any(marker in normalized_message for marker in destroyed_markers)


def _set_window_title(*, figure: object, title: str) -> None:
    canvas = getattr(figure, "canvas", None)
    manager = getattr(canvas, "manager", None)
    set_window_title = getattr(manager, "set_window_title", None)
    if not callable(set_window_title):
        return

    try:
        set_window_title(title)
    except Exception as error:
        if is_destroyed_window_error(error):
            return
        raise


def _matplotlib_result_figures(result: object) -> tuple[Figure, ...]:
    from matplotlib.figure import Figure

    return tuple(figure for figure in result_figures(result) if isinstance(figure, Figure))
