"""Result-building helpers for drawing orchestration."""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

from ..config import DrawMode
from ..diagnostics import RenderDiagnostic
from ..renderers._render_support import backend_supports_interaction, figure_backend_name
from ..result import DrawResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..typing import OutputPath
    from .pipeline import PreparedDrawPipeline


def build_draw_result(
    *,
    primary_figure: Figure,
    primary_axes: Axes,
    figures: tuple[Figure, ...],
    axes: tuple[Axes, ...],
    mode: DrawMode,
    page_count: int,
    diagnostics: tuple[RenderDiagnostic, ...],
    pipeline: PreparedDrawPipeline,
    output: OutputPath | None,
) -> DrawResult:
    """Build the normalized public ``DrawResult`` contract."""

    hover_enabled = pipeline.draw_options.hover.enabled
    return DrawResult(
        primary_figure=primary_figure,
        primary_axes=primary_axes,
        figures=figures,
        axes=axes,
        mode=mode,
        page_count=page_count,
        diagnostics=diagnostics,
        detected_framework=pipeline.detected_framework,
        interactive_enabled=interactive_enabled_for_result(
            figure=primary_figure,
            mode=mode,
            pipeline=pipeline,
        ),
        hover_enabled=hover_enabled,
        saved_path=normalized_saved_path(output),
    )


def interactive_enabled_for_result(
    *,
    figure: Figure,
    mode: DrawMode,
    pipeline: PreparedDrawPipeline,
) -> bool:
    """Return whether the resulting figure still supports interaction."""

    from . import api as drawing_api

    backend_name_resolver = getattr(drawing_api, "figure_backend_name", figure_backend_name)
    if not backend_supports_interaction(backend_name_resolver(figure)):
        return False
    if mode in frozenset({DrawMode.SLIDER, DrawMode.PAGES_CONTROLS}):
        return True
    if pipeline.draw_options.hover.enabled:
        return True
    return pipeline.draw_options.view == "3d"


def normalized_saved_path(output: object) -> str | None:
    """Normalize one output path into the public saved-path string."""

    if output is None:
        return None
    if isinstance(output, str | PathLike):
        return str(Path(output).resolve())
    return str(Path(str(output)).resolve())


def combined_draw_diagnostics(
    *diagnostic_groups: tuple[RenderDiagnostic, ...],
) -> tuple[RenderDiagnostic, ...]:
    """Merge draw diagnostics while preserving order."""

    diagnostics: list[RenderDiagnostic] = []
    for diagnostic_group in diagnostic_groups:
        diagnostics.extend(diagnostic_group)
    return tuple(diagnostics)
