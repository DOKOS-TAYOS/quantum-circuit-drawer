"""Public result objects returned by draw operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ._ipython_display import display_figures_in_ipython
from .config import DrawMode, normalize_draw_mode
from .diagnostics import DiagnosticSeverity, RenderDiagnostic
from .export.figures import save_matplotlib_figure
from .typing import OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure


@dataclass(frozen=True, slots=True)
class DrawResult:
    """Result returned by ``draw_quantum_circuit(...)``.

    Attributes:
        primary_figure: Most useful Matplotlib figure for the call. In paged modes this
            is the first page or the managed container figure.
        primary_axes: Most useful axes associated with ``primary_figure``.
        figures: Every Matplotlib figure produced by the call. Explicit ``pages`` mode
            can contain several figures.
        axes: Axes aligned with ``figures``.
        mode: Effective ``DrawMode`` after resolving ``auto``.
        page_count: Number of rendered or available pages.
        diagnostics: Non-fatal diagnostics emitted while preparing or rendering.
        detected_framework: Adapter selected for the input circuit.
        interactive_enabled: Whether the result contains managed interactive controls.
        hover_enabled: Whether hover annotations are active.
        saved_path: Absolute saved path when ``output_path`` was used.
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
    _ipython_display_enabled: bool = field(default=True, repr=False, compare=False)
    _ipython_close_after_display: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "mode", normalize_draw_mode(self.mode))

    def _ipython_display_(self) -> None:
        """Display contained figures in IPython without showing the dataclass repr."""

        if not self._ipython_display_enabled:
            return
        display_figures_in_ipython(
            self.figures,
            close_after_display=self._ipython_close_after_display,
        )

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
        """Save the primary figure to disk.

        Args:
            path: Destination image path accepted by Matplotlib.

        Returns:
            The absolute path written.
        """

        save_matplotlib_figure(self.primary_figure, path)
        return _resolved_output_path(path)

    def save_all_pages(
        self,
        output_dir: OutputPath,
        *,
        filename_prefix: str = "page",
        extension: str = ".png",
    ) -> tuple[str, ...]:
        """Save every figure page to one directory.

        Args:
            output_dir: Directory to create or reuse for exported pages.
            filename_prefix: Prefix used before the 1-based page number.
            extension: Image extension such as ``".png"``, ``"png"``, or ``".svg"``.

        Returns:
            Absolute paths written, one per figure in ``figures``.
        """

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
        """Return draw metadata without Matplotlib objects.

        Returns:
            A JSON-friendly dictionary with mode, page count, framework, interactivity,
            hover state, saved path, and diagnostics.
        """

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
    """Return diagnostics as JSON-friendly dictionaries.

    Args:
        diagnostics: Diagnostics to serialize.

    Returns:
        Tuple of dictionaries with ``code``, ``message``, and ``severity`` keys.
    """

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
