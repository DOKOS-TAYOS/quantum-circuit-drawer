"""Shared renderer utilities for saving figures and backend detection."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..export.figures import save_matplotlib_figure
from ..typing import OutputPath

if TYPE_CHECKING:
    from matplotlib.figure import Figure, SubFigure

NON_INTERACTIVE_BACKENDS = frozenset({"agg", "cairo", "pdf", "pgf", "ps", "svg", "template"})
NOTEBOOK_INTERACTIVE_BACKENDS = frozenset({"nbagg", "ipympl", "widget"})


def save_rendered_figure(
    figure: Figure | SubFigure,
    output: OutputPath | None,
) -> None:
    """Save a Matplotlib figure or subfigure with consistent error handling."""

    save_matplotlib_figure(
        figure,
        output,
        error_message_prefix="failed to save rendered circuit to",
        bbox_inches="tight",
    )


def close_figure_best_effort(
    figure: Figure | SubFigure,
    *,
    logger: logging.Logger,
    context: str,
) -> None:
    """Attempt to close one figure without masking the main render outcome."""

    from matplotlib import pyplot as plt

    try:
        plt.close(figure)
    except Exception:
        logger.warning("Failed best-effort cleanup for %s.", context, exc_info=True)


def show_figure_if_supported(figure: Figure | SubFigure, *, show: bool) -> None:
    """Call ``pyplot.show()`` only when it is meaningful for the active backend."""

    if not show:
        return

    from matplotlib import pyplot as plt

    show_function = plt.show
    backend_name = figure_backend_name(figure)
    if backend_name in NON_INTERACTIVE_BACKENDS and is_builtin_pyplot_show(show_function):
        return
    if backend_name in NOTEBOOK_INTERACTIVE_BACKENDS and is_builtin_pyplot_show(show_function):
        return

    show_function()


def pyplot_backend_name() -> str:
    """Return the normalized name of the current pyplot backend."""

    from matplotlib import pyplot as plt

    return normalize_backend_name(str(plt.get_backend()))


def backend_supports_interaction(backend_name: str) -> bool:
    """Return whether the normalized backend can keep Matplotlib interactivity alive."""

    return backend_name not in NON_INTERACTIVE_BACKENDS


def pyplot_backend_supports_interaction() -> bool:
    """Return whether the current pyplot backend is interactive."""

    return backend_supports_interaction(pyplot_backend_name())


def should_use_managed_agg_canvas(
    *,
    show: bool,
    output: OutputPath | None,
    prefer_offscreen_when_hidden: bool = False,
) -> bool:
    """Return whether managed rendering should force an Agg canvas."""

    if output is not None:
        return True
    if show:
        return False
    if prefer_offscreen_when_hidden:
        return True
    return not pyplot_backend_supports_interaction()


def is_builtin_pyplot_show(show_function: object) -> bool:
    """Return whether the current show function is Matplotlib's builtin pyplot.show."""

    return getattr(show_function, "__module__", "") == "matplotlib.pyplot"


def figure_backend_name(figure: Figure | SubFigure) -> str:
    """Resolve a normalized backend name from a figure canvas."""

    canvas_name = type(figure.canvas).__name__.lower()
    if canvas_name.startswith("figurecanvas"):
        return normalize_backend_name(canvas_name.removeprefix("figurecanvas"))

    from matplotlib import pyplot as plt

    return normalize_backend_name(str(plt.get_backend()))


def normalize_backend_name(backend_name: str) -> str:
    """Normalize Matplotlib backend names into their short lowercase form."""

    normalized_name = backend_name.strip().lower()
    for prefix in (
        "module://matplotlib.backends.backend_",
        "matplotlib.backends.backend_",
        "backend_",
    ):
        if normalized_name.startswith(prefix):
            normalized_name = normalized_name.removeprefix(prefix)
    return normalized_name
