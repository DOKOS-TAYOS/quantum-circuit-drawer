"""Shared helpers for renderer-managed Matplotlib figures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure, SubFigure

if TYPE_CHECKING:
    from ..layout.scene import LayoutScene

_MANAGED_SUBPLOT_LEFT = 0.02
_MANAGED_SUBPLOT_RIGHT = 0.98
_MANAGED_SUBPLOT_TOP = 0.98
_MANAGED_SUBPLOT_BOTTOM = 0.02
_METADATA_ATTR = "_quantum_circuit_drawer_metadata"


@dataclass(slots=True)
class _ManagedFigureMetadata:
    viewport_width: float | None = None
    page_slider: object | None = None


def create_managed_figure(
    scene: LayoutScene,
    *,
    figure_width: float | None = None,
    figure_height: float | None = None,
    use_agg: bool = False,
) -> tuple[Figure, Axes]:
    """Create a managed Matplotlib figure with consistent padding."""

    figsize = (
        figure_width if figure_width is not None else max(4.6, scene.width * 0.95),
        figure_height if figure_height is not None else max(2.1, scene.height * 0.72),
    )

    if use_agg:
        figure = Figure(figsize=figsize)
        FigureCanvasAgg(figure)
    else:
        from matplotlib import pyplot as plt

        figure = plt.figure(figsize=figsize)

    axes = figure.add_subplot(111)
    figure.subplots_adjust(
        left=_MANAGED_SUBPLOT_LEFT,
        right=_MANAGED_SUBPLOT_RIGHT,
        top=_MANAGED_SUBPLOT_TOP,
        bottom=_MANAGED_SUBPLOT_BOTTOM,
    )
    return figure, axes


def set_viewport_width(figure: Figure | SubFigure, *, viewport_width: float) -> None:
    """Store the effective viewport width used by text fitting."""

    _metadata_for(figure).viewport_width = viewport_width


def get_viewport_width(figure: Figure | SubFigure, *, default: float) -> float:
    """Return the stored viewport width or a provided default."""

    viewport_width = _metadata_for(figure).viewport_width
    if viewport_width is None:
        return default
    return viewport_width


def set_page_slider(figure: Figure | SubFigure, page_slider: object) -> None:
    """Store the page slider attached to a managed figure."""

    _metadata_for(figure).page_slider = page_slider


def get_page_slider(figure: Figure | SubFigure) -> object | None:
    """Return the stored page slider if one has been attached."""

    return _metadata_for(figure).page_slider


def _metadata_for(figure: Figure | SubFigure) -> _ManagedFigureMetadata:
    metadata = getattr(figure, _METADATA_ATTR, None)
    if isinstance(metadata, _ManagedFigureMetadata):
        return metadata

    metadata = _ManagedFigureMetadata()
    setattr(figure, _METADATA_ATTR, metadata)
    return metadata
