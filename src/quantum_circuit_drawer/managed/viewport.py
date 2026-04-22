"""Viewport-aware helpers for managed 2D draw orchestration."""

from __future__ import annotations

import math

from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure

from ..ir.circuit import CircuitIR
from ..layout.scene import LayoutScene
from ..style import DrawStyle
from ..typing import LayoutEngineLike


def build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a continuous-width 2D scene for page-slider mode."""

    from ._adaptive_paging import build_continuous_slider_scene as _build_continuous_slider_scene

    return _build_continuous_slider_scene(
        circuit,
        layout_engine,
        style,
        hover_enabled=hover_enabled,
    )


def viewport_adaptive_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    axes: Axes,
    *,
    hover_enabled: bool = True,
    initial_scene: LayoutScene | None = None,
) -> tuple[LayoutScene, float]:
    """Return the paged scene whose aspect best matches the current axes viewport."""

    from ._adaptive_paging import viewport_adaptive_paged_scene as _viewport_adaptive_paged_scene

    return _viewport_adaptive_paged_scene(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
    )


def compute_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a paged 2D scene using the provided normalized style."""

    from ._adaptive_paging import compute_paged_scene as _compute_paged_scene

    return _compute_paged_scene(
        circuit,
        layout_engine,
        style,
        hover_enabled=hover_enabled,
    )


def page_window_adaptive_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    axes: Axes,
    *,
    hover_enabled: bool = True,
    initial_scene: LayoutScene | None = None,
    visible_page_count: int = 1,
) -> tuple[LayoutScene, float]:
    """Return the paged scene that best fits the visible page-window stack."""

    from ._adaptive_paging import (
        page_window_adaptive_paged_scene as _page_window_adaptive_paged_scene,
    )

    return _page_window_adaptive_paged_scene(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
        visible_page_count=visible_page_count,
    )


def axes_viewport_ratio(axes: Axes) -> float:
    """Return the current visible axes aspect ratio in pixels."""

    viewport_width, viewport_height = axes_viewport_pixels(axes)
    if viewport_width <= 0.0 or viewport_height <= 0.0:
        return 0.0
    return viewport_width / viewport_height


def axes_viewport_pixels(axes: Axes) -> tuple[float, float]:
    """Return the current axes viewport size in pixels."""

    figure_width, figure_height = _figure_size_inches(axes.figure)
    axes_position = axes.get_position(original=True)
    viewport_width = figure_width * axes.figure.dpi * axes_position.width
    viewport_height = figure_height * axes.figure.dpi * axes_position.height
    return viewport_width, viewport_height


def scene_aspect_ratio(scene: LayoutScene) -> float:
    """Return the width-to-height ratio of a 2D scene."""

    if scene.height <= 0.0:
        return scene.width
    return scene.width / scene.height


def viewport_scene_score(scene: LayoutScene, viewport_ratio: float) -> float:
    """Return how closely the scene aspect matches the viewport aspect."""

    return _viewport_scene_score_for_size(scene.width, scene.height, viewport_ratio)


def _figure_size_inches(figure: Figure | SubFigure) -> tuple[float, float]:
    if isinstance(figure, Figure):
        size_inches = figure.get_size_inches()
    else:
        size_inches = figure.figure.get_size_inches()
    return float(size_inches[0]), float(size_inches[1])


def _scene_aspect_ratio_for_size(scene_width: float, scene_height: float) -> float:
    if scene_height <= 0.0:
        return scene_width
    return scene_width / scene_height


def _viewport_scene_score_for_size(
    scene_width: float,
    scene_height: float,
    viewport_ratio: float,
) -> float:
    scene_ratio = max(_scene_aspect_ratio_for_size(scene_width, scene_height), 1e-6)
    if viewport_ratio <= 0.0:
        return math.inf
    return abs(math.log(scene_ratio / viewport_ratio))
