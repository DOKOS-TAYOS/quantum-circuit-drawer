"""Shared renderer utilities for saving figures and backend detection."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..exceptions import RenderingError
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

    if output is None:
        return

    try:
        from matplotlib.figure import SubFigure as MatplotlibSubFigure

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_figure = figure.figure if isinstance(figure, MatplotlibSubFigure) else figure
        save_figure.savefig(output_path, bbox_inches="tight")
    except (OSError, TypeError, ValueError) as exc:
        raise RenderingError(f"failed to save rendered circuit to {output!r}: {exc}") from exc


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
