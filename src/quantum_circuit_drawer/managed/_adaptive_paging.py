"""Adaptive managed paging heuristics."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from matplotlib.axes import Axes

from ..ir.circuit import CircuitIR
from ..layout._layout_scaffold import (
    _LayoutPagingInputs,
    build_layout_paging_inputs,
    paged_scene_metrics_for_width,
)
from ..layout.scene import LayoutScene, ScenePage
from ..style import DrawStyle
from ..style.defaults import replace_draw_style
from ..typing import LayoutEngineLike
from .viewport import (
    _scene_aspect_ratio_for_size,
    _viewport_scene_score_for_size,
    axes_viewport_ratio,
)

_VIEWPORT_SEARCH_STEPS = 10


@dataclass(frozen=True, slots=True)
class _AdaptivePagingMetrics:
    pages: tuple[ScenePage, ...]
    scene_width: float
    scene_height: float


def build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a continuous-width 2D scene for page-slider mode."""

    slider_style = replace_draw_style(style, max_page_width=float("inf"))
    return _compute_layout_scene(
        circuit,
        layout_engine,
        slider_style,
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

    return _adaptive_paged_scene(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
        viewport_size_resolver=_full_scene_viewport_size,
    )


def compute_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a paged 2D scene using the provided normalized style."""

    return _compute_layout_scene(
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

    clamped_visible_page_count = max(1, visible_page_count)
    return _adaptive_paged_scene(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
        viewport_size_resolver=lambda candidate_metrics, paging_inputs: _page_window_viewport_size(
            candidate_metrics,
            paging_inputs,
            visible_page_count=clamped_visible_page_count,
        ),
    )


def _compute_layout_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool,
) -> LayoutScene:
    from ..layout.engine import LayoutEngine

    if isinstance(layout_engine, LayoutEngine):
        return layout_engine._compute_with_normalized_style(
            circuit,
            style,
            hover_enabled=hover_enabled,
        )
    return layout_engine.compute(circuit, style)


def _adaptive_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    axes: Axes,
    *,
    hover_enabled: bool,
    initial_scene: LayoutScene | None,
    viewport_size_resolver: Callable[
        [_AdaptivePagingMetrics, _LayoutPagingInputs],
        tuple[float, float],
    ],
) -> tuple[LayoutScene, float]:
    max_page_width = style.max_page_width
    viewport_ratio = axes_viewport_ratio(axes)
    if viewport_ratio <= 0.0:
        if initial_scene is not None:
            return initial_scene, max_page_width
        return (
            compute_paged_scene(
                circuit,
                layout_engine,
                style,
                hover_enabled=hover_enabled,
            ),
            max_page_width,
        )

    paging_inputs = build_layout_paging_inputs(circuit, style)
    continuous_metrics = _adaptive_paging_metrics_for_width(
        paging_inputs,
        max_page_width=float("inf"),
    )
    continuous_page_width = (
        continuous_metrics.pages[0].content_width
        if continuous_metrics.pages
        else continuous_metrics.scene_width
    )
    if not math.isfinite(max_page_width):
        if initial_scene is not None:
            return initial_scene, continuous_page_width
        return (
            build_continuous_slider_scene(
                circuit,
                layout_engine,
                style,
                hover_enabled=hover_enabled,
            ),
            continuous_page_width,
        )

    lower_bound = min(style.gate_width, max_page_width)
    upper_bound = max(max_page_width, continuous_page_width)
    metrics_cache: dict[float, _AdaptivePagingMetrics] = {upper_bound: continuous_metrics}

    def candidate_metrics(page_width: float) -> _AdaptivePagingMetrics:
        cached_metrics = metrics_cache.get(page_width)
        if cached_metrics is not None:
            return cached_metrics
        resolved_metrics = _adaptive_paging_metrics_for_width(
            paging_inputs,
            max_page_width=page_width,
        )
        metrics_cache[page_width] = resolved_metrics
        return resolved_metrics

    best_page_width = upper_bound
    best_width, best_height = viewport_size_resolver(continuous_metrics, paging_inputs)
    best_score = _viewport_scene_score_for_size(best_width, best_height, viewport_ratio)

    low = lower_bound
    high = upper_bound
    for page_width in (low, high):
        candidate_width, candidate_height = viewport_size_resolver(
            candidate_metrics(page_width),
            paging_inputs,
        )
        candidate_score = _viewport_scene_score_for_size(
            candidate_width,
            candidate_height,
            viewport_ratio,
        )
        if candidate_score < best_score:
            best_page_width = page_width
            best_score = candidate_score

    for _ in range(_VIEWPORT_SEARCH_STEPS):
        mid = (low + high) / 2.0
        candidate_width, candidate_height = viewport_size_resolver(
            candidate_metrics(mid),
            paging_inputs,
        )
        candidate_ratio = _scene_aspect_ratio_for_size(candidate_width, candidate_height)
        candidate_score = _viewport_scene_score_for_size(
            candidate_width,
            candidate_height,
            viewport_ratio,
        )
        if candidate_score < best_score:
            best_page_width = mid
            best_score = candidate_score
        if candidate_ratio <= viewport_ratio:
            low = mid
            continue
        high = mid

    if initial_scene is not None and math.isclose(
        best_page_width,
        max_page_width,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return initial_scene, best_page_width
    return (
        compute_paged_scene(
            circuit,
            layout_engine,
            replace_draw_style(style, max_page_width=best_page_width),
            hover_enabled=hover_enabled,
        ),
        best_page_width,
    )


def _adaptive_paging_metrics_for_width(
    paging_inputs: _LayoutPagingInputs,
    *,
    max_page_width: float,
) -> _AdaptivePagingMetrics:
    candidate = paged_scene_metrics_for_width(
        paging_inputs,
        max_page_width=max_page_width,
    )
    return _AdaptivePagingMetrics(
        pages=candidate.pages,
        scene_width=candidate.scene_width,
        scene_height=candidate.scene_height,
    )


def _full_scene_viewport_size(
    candidate_metrics: _AdaptivePagingMetrics,
    _paging_inputs: _LayoutPagingInputs,
) -> tuple[float, float]:
    return candidate_metrics.scene_width, candidate_metrics.scene_height


def _page_window_viewport_size(
    candidate_metrics: _AdaptivePagingMetrics,
    paging_inputs: _LayoutPagingInputs,
    *,
    visible_page_count: int,
) -> tuple[float, float]:
    style = paging_inputs.draw_style
    window_width = max(
        (
            style.margin_left + page.content_width + style.margin_right
            for page in candidate_metrics.pages
        ),
        default=candidate_metrics.scene_width,
    )
    page_stack_count = min(max(1, visible_page_count), max(1, len(candidate_metrics.pages)))
    window_height = paging_inputs.page_height + (
        (page_stack_count - 1) * (paging_inputs.page_height + style.page_vertical_gap)
    )
    return window_width, window_height
