"""Public result objects returned by draw operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from .config import DrawMode
from .diagnostics import DiagnosticSeverity, RenderDiagnostic
from .export.figures import save_matplotlib_figure
from .typing import OutputPath

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

    def save(self, path: OutputPath) -> str:
        """Save the primary figure and return the absolute saved path."""

        save_matplotlib_figure(self.primary_figure, path)
        return _resolved_output_path(path)

    def save_all_pages(
        self,
        output_dir: OutputPath,
        *,
        filename_prefix: str = "page",
        extension: str = ".png",
    ) -> tuple[str, ...]:
        """Save every figure page and return absolute saved paths."""

        output_directory = Path(output_dir)
        output_directory.mkdir(parents=True, exist_ok=True)
        normalized_extension = extension if extension.startswith(".") else f".{extension}"
        saved_paths: list[str] = []
        for index, figure in enumerate(self.figures, start=1):
            output_path = output_directory / f"{filename_prefix}_{index}{normalized_extension}"
            save_matplotlib_figure(figure, output_path)
            saved_paths.append(_resolved_output_path(output_path))
        return tuple(saved_paths)

    def to_dict(self) -> dict[str, object]:
        """Return result metadata without Matplotlib figure or axes objects."""

        return {
            "mode": self.mode.value,
            "page_count": self.page_count,
            "detected_framework": self.detected_framework,
            "interactive_enabled": self.interactive_enabled,
            "hover_enabled": self.hover_enabled,
            "saved_path": self.saved_path,
            "diagnostics": diagnostics_to_dicts(self.diagnostics),
        }


def diagnostics_to_dicts(
    diagnostics: tuple[RenderDiagnostic, ...],
) -> tuple[dict[str, str], ...]:
    """Return diagnostics as JSON-friendly dictionaries."""

    return tuple(
        {
            "code": diagnostic.code,
            "message": diagnostic.message,
            "severity": diagnostic.severity.value,
        }
        for diagnostic in diagnostics
    )


def _resolved_output_path(path: OutputPath) -> str:
    return str(Path(path).resolve())
