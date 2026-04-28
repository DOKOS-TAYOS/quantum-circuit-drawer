"""Adaptive managed paging heuristics."""

from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Literal

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

_VIEWPORT_SCORE_EARLY_EXIT_TOLERANCE = 0.015
_VIEWPORT_SEARCH_MAX_STEPS = 8
_VIEWPORT_SEARCH_MIN_STEPS = 5
_PAGE_WIDTH_EARLY_EXIT_INTERVAL_FRACTION = 0.05
_MANAGED_2D_SCENE_FACTORY_CACHE_LIMIT = 16

_SceneFactoryMode = Literal["full", "page_window"]
_SceneFactoryCacheKey = tuple[int, int, int, bool]
_scene_factory_cache: OrderedDict[_SceneFactoryCacheKey, _Managed2DSceneFactory] = OrderedDict()


@dataclass(frozen=True, slots=True)
class _AdaptivePagingMetrics:
    pages: tuple[ScenePage, ...]
    scene_width: float
    scene_height: float


@dataclass(frozen=True, slots=True)
class _EvaluatedPageWidth:
    page_width: float
    metrics: _AdaptivePagingMetrics
    viewport_width: float
    viewport_height: float
    viewport_ratio: float
    score: float


@dataclass(slots=True)
class _Managed2DSceneFactory:
    """Reuse paging inputs, adaptive metrics, and prepared 2D scenes."""

    circuit: CircuitIR
    layout_engine: LayoutEngineLike
    style: DrawStyle
    hover_enabled: bool
    paging_inputs: _LayoutPagingInputs = field(init=False)
    adaptive_metrics_cache: dict[float, _AdaptivePagingMetrics] = field(default_factory=dict)
    paged_scene_cache: dict[float, LayoutScene] = field(default_factory=dict)
    continuous_window_scene_cache: dict[tuple[int, int], LayoutScene] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.paging_inputs = build_layout_paging_inputs(self.circuit, self.style)

    def metrics_for_page_width(self, page_width: float) -> _AdaptivePagingMetrics:
        cached_metrics = self.adaptive_metrics_cache.get(page_width)
        if cached_metrics is not None:
            return cached_metrics
        resolved_metrics = _adaptive_paging_metrics_for_width(
            self.paging_inputs,
            max_page_width=page_width,
        )
        self.adaptive_metrics_cache[page_width] = resolved_metrics
        return resolved_metrics

    def scene_for_page_width(self, page_width: float) -> LayoutScene:
        cached_scene = self.paged_scene_cache.get(page_width)
        if cached_scene is not None:
            return cached_scene
        scene = _compute_layout_scene(
            self.circuit,
            self.layout_engine,
            replace_draw_style(self.style, max_page_width=page_width),
            hover_enabled=self.hover_enabled,
        )
        self.paged_scene_cache[page_width] = scene
        return scene

    def remember_scene_for_page_width(self, page_width: float, scene: LayoutScene) -> None:
        self.paged_scene_cache[page_width] = scene

    def continuous_scene_for_column_window(
        self,
        *,
        start_column: int,
        end_column: int,
    ) -> LayoutScene:
        cache_key = (start_column, end_column)
        cached_scene = self.continuous_window_scene_cache.get(cache_key)
        if cached_scene is not None:
            return cached_scene
        windowed_circuit = _circuit_column_window(
            self.circuit,
            start_column=start_column,
            end_column=end_column,
        )
        scene = _compute_layout_scene(
            windowed_circuit,
            self.layout_engine,
            replace_draw_style(self.style, max_page_width=float("inf")),
            hover_enabled=self.hover_enabled,
        )
        self.continuous_window_scene_cache[cache_key] = scene
        return scene

    def best_page_width_for_axes(
        self,
        axes: Axes,
        *,
        visible_page_count: int = 1,
        mode: _SceneFactoryMode,
    ) -> float:
        viewport_ratio = axes_viewport_ratio(axes)
        if viewport_ratio <= 0.0:
            return self.style.max_page_width

        max_page_width = self.style.max_page_width
        continuous_metrics = self.metrics_for_page_width(float("inf"))
        continuous_page_width = (
            continuous_metrics.pages[0].content_width
            if continuous_metrics.pages
            else continuous_metrics.scene_width
        )
        continuous_candidate = _evaluate_page_width_candidate_from_metrics(
            page_width=continuous_page_width,
            metrics=continuous_metrics,
            viewport_ratio=viewport_ratio,
            paging_inputs=self.paging_inputs,
            mode=mode,
            visible_page_count=visible_page_count,
        )
        if not math.isfinite(max_page_width):
            return continuous_page_width

        if continuous_candidate.score <= _VIEWPORT_SCORE_EARLY_EXIT_TOLERANCE:
            return continuous_page_width

        max_page_width_candidate = _evaluate_page_width_candidate(
            self,
            page_width=max_page_width,
            viewport_ratio=viewport_ratio,
            mode=mode,
            visible_page_count=visible_page_count,
        )
        if _can_return_max_page_width_early(
            continuous_candidate=continuous_candidate,
            max_page_width_candidate=max_page_width_candidate,
        ):
            return max_page_width

        lower_bound = min(self.style.gate_width, max_page_width)
        upper_bound = max(max_page_width, continuous_page_width)
        low = lower_bound
        high = upper_bound
        best_page_width = upper_bound
        best_score = continuous_candidate.score

        lower_bound_candidate = max_page_width_candidate
        if max_page_width_candidate.score < best_score:
            best_page_width = max_page_width_candidate.page_width
            best_score = max_page_width_candidate.score
        if not math.isclose(lower_bound, max_page_width, rel_tol=1e-9, abs_tol=1e-9):
            lower_bound_candidate = _evaluate_page_width_candidate(
                self,
                page_width=lower_bound,
                viewport_ratio=viewport_ratio,
                mode=mode,
                visible_page_count=visible_page_count,
            )
            if lower_bound_candidate.score < best_score:
                best_page_width = lower_bound_candidate.page_width
                best_score = lower_bound_candidate.score

        if (upper_bound - lower_bound) <= _page_width_search_interval_threshold(
            self.style.gate_width
        ):
            return best_page_width

        search_steps = _adaptive_search_step_budget(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            gate_width=self.style.gate_width,
        )
        for _ in range(search_steps):
            mid = (low + high) / 2.0
            candidate = _evaluate_page_width_candidate(
                self,
                page_width=mid,
                viewport_ratio=viewport_ratio,
                mode=mode,
                visible_page_count=visible_page_count,
            )
            if candidate.score < best_score:
                best_page_width = candidate.page_width
                best_score = candidate.score
            if candidate.viewport_ratio <= viewport_ratio:
                low = mid
                continue
            high = mid

        return best_page_width


def build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a continuous-width 2D scene for page-slider mode."""

    scene_factory = managed_2d_scene_factory(
        circuit,
        layout_engine,
        style,
        hover_enabled=hover_enabled,
    )
    return scene_factory.scene_for_page_width(float("inf"))


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
        managed_2d_scene_factory(
            circuit,
            layout_engine,
            style,
            hover_enabled=hover_enabled,
        ),
        axes,
        initial_scene=initial_scene,
        mode="full",
    )


def compute_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a paged 2D scene using the provided normalized style."""

    scene_factory = managed_2d_scene_factory(
        circuit,
        layout_engine,
        style,
        hover_enabled=hover_enabled,
    )
    return scene_factory.scene_for_page_width(style.max_page_width)


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
        managed_2d_scene_factory(
            circuit,
            layout_engine,
            style,
            hover_enabled=hover_enabled,
        ),
        axes,
        initial_scene=initial_scene,
        mode="page_window",
        visible_page_count=clamped_visible_page_count,
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
    scene_factory: _Managed2DSceneFactory,
    axes: Axes,
    *,
    initial_scene: LayoutScene | None,
    mode: _SceneFactoryMode,
    visible_page_count: int = 1,
) -> tuple[LayoutScene, float]:
    max_page_width = scene_factory.style.max_page_width
    viewport_ratio = axes_viewport_ratio(axes)
    if viewport_ratio <= 0.0:
        if initial_scene is not None:
            return initial_scene, max_page_width
        return scene_factory.scene_for_page_width(max_page_width), max_page_width

    best_page_width = scene_factory.best_page_width_for_axes(
        axes,
        mode=mode,
        visible_page_count=visible_page_count,
    )
    if initial_scene is not None and math.isclose(
        best_page_width,
        max_page_width,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        return initial_scene, best_page_width
    return scene_factory.scene_for_page_width(best_page_width), best_page_width


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


def _evaluate_page_width_candidate(
    scene_factory: _Managed2DSceneFactory,
    *,
    page_width: float,
    viewport_ratio: float,
    mode: _SceneFactoryMode,
    visible_page_count: int,
) -> _EvaluatedPageWidth:
    metrics = scene_factory.metrics_for_page_width(page_width)
    return _evaluate_page_width_candidate_from_metrics(
        page_width=page_width,
        metrics=metrics,
        viewport_ratio=viewport_ratio,
        paging_inputs=scene_factory.paging_inputs,
        mode=mode,
        visible_page_count=visible_page_count,
    )


def _evaluate_page_width_candidate_from_metrics(
    *,
    page_width: float,
    metrics: _AdaptivePagingMetrics,
    viewport_ratio: float,
    paging_inputs: _LayoutPagingInputs,
    mode: _SceneFactoryMode,
    visible_page_count: int,
) -> _EvaluatedPageWidth:
    viewport_width, viewport_height = _viewport_size_for_mode(
        metrics,
        paging_inputs,
        mode=mode,
        visible_page_count=visible_page_count,
    )
    candidate_viewport_ratio = _scene_aspect_ratio_for_size(viewport_width, viewport_height)
    score = _viewport_scene_score_for_size(
        viewport_width,
        viewport_height,
        viewport_ratio,
    )
    return _EvaluatedPageWidth(
        page_width=page_width,
        metrics=metrics,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
        viewport_ratio=candidate_viewport_ratio,
        score=score,
    )


def _can_return_max_page_width_early(
    *,
    continuous_candidate: _EvaluatedPageWidth,
    max_page_width_candidate: _EvaluatedPageWidth,
) -> bool:
    return (
        max_page_width_candidate.score <= _VIEWPORT_SCORE_EARLY_EXIT_TOLERANCE
        and max_page_width_candidate.score <= continuous_candidate.score
        and max_page_width_candidate.viewport_ratio <= continuous_candidate.viewport_ratio
    )


def _adaptive_search_step_budget(
    *,
    lower_bound: float,
    upper_bound: float,
    gate_width: float,
) -> int:
    interval = max(0.0, upper_bound - lower_bound)
    normalized_gate_width = max(gate_width, 1e-6)
    normalized_interval = max(1.0, interval / normalized_gate_width)
    return max(
        _VIEWPORT_SEARCH_MIN_STEPS,
        min(
            _VIEWPORT_SEARCH_MAX_STEPS,
            math.ceil(math.log2(normalized_interval + 1.0)),
        ),
    )


def _page_width_search_interval_threshold(gate_width: float) -> float:
    return max(1e-6, gate_width * _PAGE_WIDTH_EARLY_EXIT_INTERVAL_FRACTION)


def managed_2d_scene_factory(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool,
) -> _Managed2DSceneFactory:
    cache_key = (id(circuit), id(layout_engine), id(style), hover_enabled)
    cached_factory = _scene_factory_cache.get(cache_key)
    if cached_factory is not None:
        _scene_factory_cache.move_to_end(cache_key)
        return cached_factory

    scene_factory = _Managed2DSceneFactory(
        circuit=circuit,
        layout_engine=layout_engine,
        style=style,
        hover_enabled=hover_enabled,
    )
    _scene_factory_cache[cache_key] = scene_factory
    while len(_scene_factory_cache) > _MANAGED_2D_SCENE_FACTORY_CACHE_LIMIT:
        _scene_factory_cache.popitem(last=False)
    return scene_factory


def _viewport_size_for_mode(
    candidate_metrics: _AdaptivePagingMetrics,
    paging_inputs: _LayoutPagingInputs,
    *,
    mode: _SceneFactoryMode,
    visible_page_count: int,
) -> tuple[float, float]:
    if mode == "page_window":
        return _page_window_viewport_size(
            candidate_metrics,
            paging_inputs,
            visible_page_count=visible_page_count,
        )
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


def _circuit_column_window(
    circuit: CircuitIR,
    *,
    start_column: int,
    end_column: int,
) -> CircuitIR:
    resolved_start_column = max(0, start_column)
    resolved_end_column = max(resolved_start_column, end_column)
    end_index = min(len(circuit.layers), resolved_end_column + 1)
    return CircuitIR(
        quantum_wires=circuit.quantum_wires,
        classical_wires=circuit.classical_wires,
        layers=tuple(circuit.layers[resolved_start_column:end_index]),
        name=circuit.name,
        metadata=dict(circuit.metadata),
    )
