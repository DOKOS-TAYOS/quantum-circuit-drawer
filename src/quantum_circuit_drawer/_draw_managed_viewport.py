"""Viewport-aware helpers for managed 2D draw orchestration."""

from __future__ import annotations

import math
from dataclasses import replace
from typing import cast

from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure

from .ir.circuit import CircuitIR
from .layout.scene import LayoutScene
from .style import DrawStyle
from .typing import LayoutEngineLike, _NormalizedLayoutEngineLike

_VIEWPORT_SEARCH_STEPS = 10


def build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
) -> LayoutScene:
    """Compute a continuous-width 2D scene for page-slider mode."""

    slider_style = replace(style, max_page_width=float("inf"))
    if hasattr(layout_engine, "_compute_with_normalized_style"):
        return cast(_NormalizedLayoutEngineLike, layout_engine)._compute_with_normalized_style(
            circuit,
            slider_style,
        )
    return layout_engine.compute(circuit, slider_style)


def viewport_adaptive_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    axes: Axes,
) -> tuple[LayoutScene, float]:
    """Return the paged scene whose aspect best matches the current axes viewport."""

    max_page_width = style.max_page_width
    viewport_ratio = axes_viewport_ratio(axes)
    if viewport_ratio <= 0.0:
        return compute_paged_scene(circuit, layout_engine, style), max_page_width

    continuous_scene = build_continuous_slider_scene(circuit, layout_engine, style)
    continuous_page_width = (
        continuous_scene.pages[0].content_width
        if continuous_scene.pages
        else continuous_scene.width
    )
    if not math.isfinite(max_page_width):
        max_page_width = continuous_page_width

    lower_bound = min(style.gate_width, max_page_width)
    upper_bound = max(max_page_width, continuous_page_width)
    scene_cache: dict[float, LayoutScene] = {}

    def scene_for_width(page_width: float) -> LayoutScene:
        cached_scene = scene_cache.get(page_width)
        if cached_scene is not None:
            return cached_scene
        scene = compute_paged_scene(
            circuit,
            layout_engine,
            replace(style, max_page_width=page_width),
        )
        scene_cache[page_width] = scene
        return scene

    best_page_width = upper_bound
    best_scene = scene_for_width(best_page_width)
    best_score = viewport_scene_score(best_scene, viewport_ratio)

    low = lower_bound
    high = upper_bound
    for page_width in (low, high):
        candidate_scene = scene_for_width(page_width)
        candidate_score = viewport_scene_score(candidate_scene, viewport_ratio)
        if candidate_score < best_score:
            best_page_width = page_width
            best_scene = candidate_scene
            best_score = candidate_score

    for _ in range(_VIEWPORT_SEARCH_STEPS):
        mid = (low + high) / 2.0
        candidate_scene = scene_for_width(mid)
        candidate_ratio = scene_aspect_ratio(candidate_scene)
        candidate_score = viewport_scene_score(candidate_scene, viewport_ratio)
        if candidate_score < best_score:
            best_page_width = mid
            best_scene = candidate_scene
            best_score = candidate_score
        if candidate_ratio <= viewport_ratio:
            low = mid
            continue
        high = mid

    return best_scene, best_page_width


def compute_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
) -> LayoutScene:
    """Compute a paged 2D scene using the provided normalized style."""

    if hasattr(layout_engine, "_compute_with_normalized_style"):
        return cast(_NormalizedLayoutEngineLike, layout_engine)._compute_with_normalized_style(
            circuit,
            style,
        )
    return layout_engine.compute(circuit, style)


def auto_paging_matches(
    *,
    current_state: object,
    candidate_scene: LayoutScene,
    candidate_page_width: float,
) -> bool:
    """Return whether a candidate scene would keep the current paging unchanged."""

    from .renderers._matplotlib_figure import AutoPagingState

    if not isinstance(current_state, AutoPagingState):
        return False
    if not math.isclose(
        current_state.effective_page_width,
        candidate_page_width,
        rel_tol=1e-6,
        abs_tol=1e-6,
    ):
        return False
    return (
        len(current_state.scene.pages) == len(candidate_scene.pages)
        and math.isclose(current_state.scene.width, candidate_scene.width, rel_tol=1e-6)
        and math.isclose(current_state.scene.height, candidate_scene.height, rel_tol=1e-6)
    )


def viewport_signature(axes: Axes) -> tuple[int, int] | None:
    """Return an integer pixel signature for the current visible axes viewport."""

    viewport_width, viewport_height = axes_viewport_pixels(axes)
    if viewport_width <= 0.0 or viewport_height <= 0.0:
        return None
    return int(round(viewport_width)), int(round(viewport_height))


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

    scene_ratio = max(scene_aspect_ratio(scene), 1e-6)
    if viewport_ratio <= 0.0:
        return math.inf
    return abs(math.log(scene_ratio / viewport_ratio))


def _figure_size_inches(figure: Figure | SubFigure) -> tuple[float, float]:
    if isinstance(figure, Figure):
        size_inches = figure.get_size_inches()
    else:
        size_inches = figure.figure.get_size_inches()
    return float(size_inches[0]), float(size_inches[1])
