"""Public result objects returned by draw operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import DrawMode

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


@dataclass(frozen=True, slots=True)
class DrawResult:
    """Normalized draw result for both managed and caller-owned figures.

    ``primary_figure`` and ``primary_axes`` give the most direct handle
    for the common case, while ``figures`` and ``axes`` expose every
    page produced by managed paged renders.
    """

    primary_figure: Figure
    primary_axes: Axes
    figures: tuple[Figure, ...]
    axes: tuple[Axes, ...]
    mode: DrawMode
    page_count: int
