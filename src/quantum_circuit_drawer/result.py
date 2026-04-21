"""Public result objects returned by draw operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .config import DrawMode
from .diagnostics import DiagnosticSeverity, RenderDiagnostic

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
    diagnostics: tuple[RenderDiagnostic, ...] = ()
    detected_framework: str | None = None
    interactive_enabled: bool = False
    hover_enabled: bool = False
    saved_path: str | None = None

    @property
    def resolved_mode(self) -> DrawMode:
        """Return the effective draw mode used for this render."""

        return self.mode

    @property
    def warnings(self) -> tuple[RenderDiagnostic, ...]:
        """Return only warning-level diagnostics for quick inspection."""

        return tuple(
            diagnostic
            for diagnostic in self.diagnostics
            if diagnostic.severity is DiagnosticSeverity.WARNING
        )
