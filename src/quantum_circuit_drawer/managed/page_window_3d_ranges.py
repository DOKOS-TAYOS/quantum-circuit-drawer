"""3D page-range calculation and adaptive balancing helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..drawing.pipeline import PreparedDrawPipeline, _compute_3d_scene
from ..ir.circuit import CircuitIR
from ..layout._layering import normalized_draw_circuit
from ..typing import LayoutEngine3DLike
from .slider_3d import circuit_window
from .viewport import page_window_adaptive_paged_scene

if TYPE_CHECKING:
    from ..layout.scene_3d import LayoutScene3D
    from ..renderers.matplotlib_renderer_3d import MatplotlibRenderer3D

_MIN_3D_PAGE_PROJECTED_ASPECT_RATIO = 1.2
_MAX_3D_PAGE_VISUAL_LOAD = 48.0


def windowed_3d_page_scenes(
    pipeline: PreparedDrawPipeline,
    *,
    figure_size: tuple[float, float] | None = None,
) -> tuple[LayoutScene3D, ...]:
    """Compute the 3D page scenes for the managed page window."""

    page_ranges = windowed_3d_page_ranges(pipeline, figure_size=figure_size)
    normalized_circuit = normalized_draw_circuit(pipeline.ir)
    return tuple(
        _compute_3d_scene(
            cast("LayoutEngine3DLike", pipeline.layout_engine),
            circuit_window(
                normalized_circuit,
                start_column=start_column,
                window_size=max(1, end_column - start_column + 1),
            ),
            pipeline.normalized_style,
            topology_name=pipeline.draw_options.topology,
            direct=pipeline.draw_options.direct,
            hover_enabled=pipeline.draw_options.hover.enabled,
        )
        for start_column, end_column in page_ranges
    )


def windowed_3d_page_ranges(
    pipeline: PreparedDrawPipeline,
    *,
    figure_size: tuple[float, float] | None = None,
    axes_bounds: tuple[float, float, float, float] | None = None,
) -> tuple[tuple[int, int], ...]:
    """Compute the page ranges used by the managed 3D page window."""

    from ..layout.engine import LayoutEngine
    from ..renderers._matplotlib_figure import create_managed_figure

    layout_engine_2d = LayoutEngine()
    initial_scene = layout_engine_2d.compute(pipeline.ir, pipeline.normalized_style)
    initial_scene.hover = pipeline.draw_options.hover
    figure_width, figure_height = figure_size or (
        max(4.6, initial_scene.width * 0.95),
        max(2.1, initial_scene.page_height * 0.72),
    )
    figure, axes = create_managed_figure(
        initial_scene,
        figure_width=figure_width,
        figure_height=figure_height,
        use_agg=True,
    )
    if axes_bounds is not None:
        axes.set_position(axes_bounds)
    try:
        adapted_scene, _ = page_window_adaptive_paged_scene(
            pipeline.ir,
            layout_engine_2d,
            pipeline.normalized_style,
            axes,
            hover_enabled=initial_scene.hover.enabled,
            initial_scene=initial_scene,
            visible_page_count=1,
        )
    finally:
        figure.clear()

    normalized_circuit = normalized_draw_circuit(pipeline.ir)
    page_ranges = tuple((page.start_column, page.end_column) for page in adapted_scene.pages) or (
        (0, max(0, len(normalized_circuit.layers) - 1)),
    )
    page_ranges = _rebalance_narrow_3d_page_ranges(
        pipeline,
        normalized_circuit=normalized_circuit,
        page_ranges=page_ranges,
        figure_size=(figure_width, figure_height),
        axes_bounds=axes_bounds,
    )
    return _rebalance_dense_3d_page_ranges(
        normalized_circuit=normalized_circuit,
        page_ranges=page_ranges,
    )


def _rebalance_narrow_3d_page_ranges(
    pipeline: PreparedDrawPipeline,
    *,
    normalized_circuit: CircuitIR,
    page_ranges: tuple[tuple[int, int], ...],
    figure_size: tuple[float, float],
    axes_bounds: tuple[float, float, float, float] | None,
) -> tuple[tuple[int, int], ...]:
    if not page_ranges:
        return page_ranges

    first_start_column, first_end_column = page_ranges[0]
    first_window_size = max(1, first_end_column - first_start_column + 1)
    if first_window_size <= 1:
        return page_ranges

    aspect_ratio_cache: dict[int, float] = {}

    def projected_aspect_ratio(window_size: int) -> float:
        cached_ratio = aspect_ratio_cache.get(window_size)
        if cached_ratio is not None:
            return cached_ratio
        scene = _compute_3d_scene(
            cast("LayoutEngine3DLike", pipeline.layout_engine),
            circuit_window(
                normalized_circuit,
                start_column=0,
                window_size=window_size,
            ),
            pipeline.normalized_style,
            topology_name=pipeline.draw_options.topology,
            direct=pipeline.draw_options.direct,
            hover_enabled=pipeline.draw_options.hover.enabled,
        )
        cached_ratio = _projected_scene_aspect_ratio(
            scene=scene,
            renderer=cast("MatplotlibRenderer3D", pipeline.renderer),
            figure_size=figure_size,
            axes_bounds=axes_bounds,
        )
        aspect_ratio_cache[window_size] = cached_ratio
        return cached_ratio

    if projected_aspect_ratio(first_window_size) >= _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO:
        return page_ranges

    low = 1
    high = first_window_size
    best_window_size = 1
    while low <= high:
        middle = (low + high) // 2
        if projected_aspect_ratio(middle) >= _MIN_3D_PAGE_PROJECTED_ASPECT_RATIO:
            best_window_size = middle
            low = middle + 1
        else:
            high = middle - 1

    if best_window_size >= first_window_size:
        return page_ranges
    return _uniform_3d_page_ranges(
        total_columns=len(normalized_circuit.layers),
        window_size=best_window_size,
    )


def _uniform_3d_page_ranges(
    *,
    total_columns: int,
    window_size: int,
) -> tuple[tuple[int, int], ...]:
    if total_columns <= 0:
        return ((0, 0),)

    ranges: list[tuple[int, int]] = []
    start_column = 0
    resolved_window_size = max(1, window_size)
    while start_column < total_columns:
        end_column = min(total_columns - 1, start_column + resolved_window_size - 1)
        ranges.append((start_column, end_column))
        start_column = end_column + 1
    return tuple(ranges)


def _rebalance_dense_3d_page_ranges(
    *,
    normalized_circuit: CircuitIR,
    page_ranges: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    if not page_ranges:
        return page_ranges

    operation_counts = tuple(len(layer.operations) for layer in normalized_circuit.layers)
    if not operation_counts:
        return page_ranges

    average_operations_per_layer = sum(operation_counts) / float(len(operation_counts))
    if average_operations_per_layer <= 0.0:
        return page_ranges

    first_start_column, first_end_column = page_ranges[0]
    first_window_size = max(1, first_end_column - first_start_column + 1)
    max_visual_window_size = max(
        1,
        int(_MAX_3D_PAGE_VISUAL_LOAD / average_operations_per_layer),
    )
    if first_window_size <= max_visual_window_size:
        return page_ranges

    return _uniform_3d_page_ranges(
        total_columns=len(normalized_circuit.layers),
        window_size=max_visual_window_size,
    )


def _projected_scene_aspect_ratio(
    *,
    scene: LayoutScene3D,
    renderer: MatplotlibRenderer3D,
    figure_size: tuple[float, float],
    axes_bounds: tuple[float, float, float, float] | None = None,
) -> float:
    from ..renderers._matplotlib_figure import create_managed_figure
    from ..renderers.matplotlib_renderer_3d import _MANAGED_3D_VIEWPORT_BOUNDS_ATTR
    from .page_window_3d_render import _display_axes_bounds

    figure, axes = create_managed_figure(
        scene,
        figure_width=figure_size[0],
        figure_height=figure_size[1],
        use_agg=True,
        projection="3d",
    )
    resolved_axes_bounds = axes_bounds or _display_axes_bounds(1)[0]
    axes_3d = axes
    axes_3d.set_position(resolved_axes_bounds)
    setattr(axes_3d, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, resolved_axes_bounds)
    try:
        renderer._prepare_axes(axes_3d, scene)
        renderer._expand_axes_to_fill_viewport(axes_3d, resolved_axes_bounds)
        renderer._synchronize_axes_geometry(axes_3d)
        render_context = renderer._create_render_context(axes_3d)
        projected_points = renderer._projected_scene_geometry_points(
            axes_3d,
            scene,
            render_context=render_context,
        )
        if projected_points.size == 0:
            return float("inf")

        x_values = tuple(float(value) for value in projected_points[:, 0])
        y_values = tuple(float(value) for value in projected_points[:, 1])
        projected_width = max(x_values) - min(x_values)
        projected_height = max(y_values) - min(y_values)
        if projected_height <= 0.0:
            return float("inf")
        return projected_width / projected_height
    finally:
        figure.clear()
