"""Shared Matplotlib figure export helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..exceptions import RenderingError
from ..typing import OutputPath

if TYPE_CHECKING:
    from matplotlib.figure import Figure, SubFigure


def save_matplotlib_figure(
    figure: Figure | SubFigure,
    output: OutputPath | None,
    *,
    error_message_prefix: str = "failed to save figure to",
    bbox_inches: str | None = None,
) -> None:
    """Save a Matplotlib figure or subfigure with consistent error handling."""

    if output is None:
        return

    try:
        from matplotlib.figure import SubFigure as MatplotlibSubFigure

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        save_target = figure.figure if isinstance(figure, MatplotlibSubFigure) else figure
        if bbox_inches is None:
            save_target.savefig(output_path)
        else:
            save_target.savefig(output_path, bbox_inches=bbox_inches)
    except (OSError, TypeError, ValueError) as exc:
        raise RenderingError(f"{error_message_prefix} {output!r}: {exc}") from exc
