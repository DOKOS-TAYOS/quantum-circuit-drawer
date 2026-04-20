"""Public API orchestration for drawing supported circuit objects."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from ._draw_pipeline import prepare_draw_pipeline
from ._draw_request import build_draw_request, validate_draw_request
from ._runtime_context import resolve_draw_config
from ._scene_pages import single_page_scenes
from .config import DrawConfig, DrawMode
from .result import DrawResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ._draw_pipeline import PreparedDrawPipeline
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D
    from .renderers.base import BaseRenderer
    from .typing import LayoutEngine3DLike, LayoutEngineLike, OutputPath

logger = logging.getLogger(__name__)


def draw_quantum_circuit(
    circuit: object,
    *,
    config: DrawConfig | None = None,
    ax: Axes | None = None,
) -> DrawResult:
    """Draw a supported circuit with the current public API contract.

    The function resolves the runtime-dependent default mode, validates
    interactive constraints, prepares the pipeline, and returns one
    normalized ``DrawResult`` for every rendering path.
    """

    resolved_config = resolve_draw_config(config, ax=ax)
    if not resolved_config.interactive_mode_allowed:
        raise ValueError(
            f"mode={resolved_config.mode.value!r} requires a notebook widget backend "
            "such as nbagg, ipympl, or widget"
        )
    if ax is not None and resolved_config.mode in {DrawMode.PAGES_CONTROLS, DrawMode.SLIDER}:
        raise ValueError(
            f"mode={resolved_config.mode.value!r} requires a Matplotlib-managed figure "
            "and cannot be used with ax"
        )

    request = build_draw_request(
        circuit=circuit,
        framework=resolved_config.config.framework,
        style=resolved_config.config.style,
        layout=resolved_config.config.layout,
        backend=resolved_config.config.backend,
        ax=ax,
        output=resolved_config.config.output_path,
        show=resolved_config.config.show,
        figsize=resolved_config.config.figsize,
        page_slider=resolved_config.mode is DrawMode.SLIDER,
        page_window=(
            resolved_config.mode is DrawMode.PAGES_CONTROLS and resolved_config.config.view == "2d"
        ),
        composite_mode=resolved_config.config.composite_mode,
        view=resolved_config.config.view,
        topology=resolved_config.config.topology,
        topology_menu=resolved_config.config.topology_menu,
        direct=resolved_config.config.direct,
        hover=resolved_config.config.hover,
        render_mode=resolved_config.mode.value,
    )
    validate_draw_request(request)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )
    pipeline = _pipeline_for_resolved_mode(pipeline, mode=resolved_config.mode)

    if request.ax is None:
        if resolved_config.mode is DrawMode.PAGES and request.pipeline_options.view == "2d":
            return _render_managed_2d_pages_result(
                pipeline,
                output=request.output,
                show=request.show,
                figsize=request.figsize,
                page_slider=request.page_slider,
                page_window=request.page_window,
                mode=resolved_config.mode,
            )
        if resolved_config.mode is DrawMode.PAGES and request.pipeline_options.view == "3d":
            return _render_managed_3d_pages_result(
                pipeline,
                output=request.output,
                show=request.show,
                figsize=request.figsize,
                mode=resolved_config.mode,
            )
        if (
            resolved_config.mode is DrawMode.PAGES_CONTROLS
            and request.pipeline_options.view == "3d"
        ):
            return _render_managed_3d_page_controls_result(
                pipeline,
                output=request.output,
                show=request.show,
                figsize=request.figsize,
                mode=resolved_config.mode,
            )
        figure, axes = _render_managed_draw_pipeline(
            pipeline,
            output=request.output,
            show=request.show,
            figsize=request.figsize,
            page_slider=request.page_slider,
            page_window=request.page_window,
        )
        return DrawResult(
            primary_figure=figure,
            primary_axes=axes,
            figures=(figure,),
            axes=(axes,),
            mode=resolved_config.mode,
            page_count=_page_count_for_pipeline(pipeline, mode=resolved_config.mode),
        )

    if request.pipeline_options.view == "3d" and not _is_3d_axes(request.ax):
        raise ValueError("view='3d' requires a 3D Matplotlib axes")
    logger.debug("Rendering scene on caller-managed Matplotlib axes")
    axes = _render_draw_pipeline_on_axes(
        pipeline,
        axes=request.ax,
        output=request.output,
    )
    figure = cast("Figure", axes.figure)
    return DrawResult(
        primary_figure=figure,
        primary_axes=axes,
        figures=(figure,),
        axes=(axes,),
        mode=resolved_config.mode,
        page_count=_page_count_for_pipeline(pipeline, mode=resolved_config.mode),
    )


def _pipeline_for_resolved_mode(
    pipeline: PreparedDrawPipeline,
    *,
    mode: DrawMode,
) -> PreparedDrawPipeline:
    if mode is not DrawMode.FULL:
        return pipeline
    if pipeline.draw_options.view != "2d":
        return pipeline

    from ._draw_managed import build_continuous_slider_scene

    layout_engine = cast("LayoutEngineLike", pipeline.layout_engine)
    continuous_scene = build_continuous_slider_scene(
        pipeline.ir,
        layout_engine,
        pipeline.normalized_style,
        hover_enabled=pipeline.draw_options.hover.enabled,
    )
    continuous_scene.hover = getattr(pipeline.paged_scene, "hover", continuous_scene.hover)
    return replace(pipeline, paged_scene=continuous_scene)


def _render_managed_draw_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
    respect_precomputed_scene: bool = False,
) -> tuple[Figure, Axes]:
    from ._draw_managed import render_managed_draw_pipeline

    return render_managed_draw_pipeline(
        pipeline,
        output=output,
        show=show,
        figsize=figsize,
        page_slider=page_slider,
        page_window=page_window,
        respect_precomputed_scene=respect_precomputed_scene,
    )


def _render_managed_2d_pages_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
    mode: DrawMode,
) -> DrawResult:
    page_scenes = single_page_scenes(cast("LayoutScene", pipeline.paged_scene))

    if output is not None:
        saved_figure, _ = _render_managed_draw_pipeline(
            pipeline,
            output=output,
            show=False,
            figsize=figsize,
            page_slider=page_slider,
            page_window=page_window,
        )
        try:
            import matplotlib.pyplot as plt

            plt.close(saved_figure)
        except Exception:  # pragma: no cover - close should be best-effort only
            pass

    figures: list[Figure] = []
    axes_list: list[Axes] = []
    for page_scene in page_scenes:
        page_pipeline = replace(pipeline, paged_scene=page_scene)
        figure, axes = _render_managed_draw_pipeline(
            page_pipeline,
            output=None,
            show=show,
            figsize=figsize,
            page_slider=False,
            page_window=False,
            respect_precomputed_scene=True,
        )
        figures.append(figure)
        axes_list.append(axes)

    return DrawResult(
        primary_figure=figures[0],
        primary_axes=axes_list[0],
        figures=tuple(figures),
        axes=tuple(axes_list),
        mode=mode,
        page_count=len(page_scenes),
    )


def _render_managed_3d_pages_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    mode: DrawMode,
) -> DrawResult:
    page_scenes = _windowed_3d_scenes(pipeline)

    if output is not None:
        _save_clean_3d_pages_output(
            page_scenes,
            renderer=pipeline.renderer,
            output=output,
            figsize=figsize,
        )

    figures: list[Figure] = []
    axes_list: list[Axes] = []
    for page_scene in page_scenes:
        page_pipeline = replace(pipeline, paged_scene=page_scene)
        figure, axes = _render_managed_draw_pipeline(
            page_pipeline,
            output=None,
            show=show,
            figsize=figsize,
            page_slider=False,
            page_window=False,
        )
        figures.append(figure)
        axes_list.append(axes)

    return DrawResult(
        primary_figure=figures[0],
        primary_axes=axes_list[0],
        figures=tuple(figures),
        axes=tuple(axes_list),
        mode=mode,
        page_count=len(page_scenes),
    )


def _render_managed_3d_page_controls_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    mode: DrawMode,
) -> DrawResult:
    from ._draw_managed_page_window_3d import configure_3d_page_window
    from ._draw_managed_topology_menu import attach_topology_menu
    from .renderers._matplotlib_figure import create_managed_figure, set_page_window
    from .renderers._render_support import should_use_managed_agg_canvas, show_figure_if_supported

    page_scenes = _windowed_3d_scenes(pipeline)
    if output is not None:
        _save_clean_3d_pages_output(
            page_scenes,
            renderer=pipeline.renderer,
            output=output,
            figsize=figsize,
        )

    scene_3d = page_scenes[0]
    use_agg_canvas = should_use_managed_agg_canvas(
        show=show,
        output=None,
        prefer_offscreen_when_hidden=not scene_3d.hover_enabled,
    )
    figure_width, figure_height = figsize or (
        max(4.6, scene_3d.width * 0.95),
        max(2.1, scene_3d.height * 0.72) + 1.0,
    )
    figure, axes = create_managed_figure(
        scene_3d,
        figure_width=figure_width,
        figure_height=figure_height,
        use_agg=use_agg_canvas,
        projection="3d",
    )
    page_window = configure_3d_page_window(
        figure=figure,
        axes=axes,
        pipeline=pipeline,
        page_scenes=page_scenes,
        set_page_window=set_page_window,
    )
    primary_axes = page_window.display_axes[0]
    if pipeline.draw_options.topology_menu and not use_agg_canvas:
        attach_topology_menu(figure=figure, axes=primary_axes, pipeline=pipeline)
    show_figure_if_supported(figure, show=show)
    return DrawResult(
        primary_figure=figure,
        primary_axes=primary_axes,
        figures=(figure,),
        axes=(primary_axes,),
        mode=mode,
        page_count=len(page_scenes),
    )


def _page_count_for_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    mode: DrawMode,
) -> int:
    if pipeline.draw_options.view != "3d":
        return len(getattr(pipeline.paged_scene, "pages", ()) or ())
    if mode is DrawMode.FULL:
        return 1
    return len(_windowed_3d_scenes(pipeline))


def _windowed_3d_scenes(pipeline: PreparedDrawPipeline) -> tuple[LayoutScene3D, ...]:
    from ._draw_managed_slider import circuit_window, page_slider_window_size
    from ._draw_pipeline import _compute_3d_scene

    layout_engine = cast("LayoutEngine3DLike", pipeline.layout_engine)
    total_columns = len(pipeline.ir.layers)
    window_size = page_slider_window_size(pipeline.ir, pipeline.normalized_style)
    start_columns = (0,) if total_columns == 0 else tuple(range(0, total_columns, window_size))
    return tuple(
        _compute_3d_scene(
            layout_engine,
            circuit_window(
                pipeline.ir,
                start_column=start_column,
                window_size=window_size,
            ),
            pipeline.normalized_style,
            topology_name=pipeline.draw_options.topology,
            direct=pipeline.draw_options.direct,
            hover_enabled=pipeline.draw_options.hover.enabled,
        )
        for start_column in start_columns
    )


def _save_clean_3d_pages_output(
    page_scenes: tuple[LayoutScene3D, ...],
    *,
    renderer: BaseRenderer,
    output: OutputPath,
    figsize: tuple[float, float] | None,
) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from .renderers._render_support import save_rendered_figure
    from .renderers.matplotlib_renderer_3d import _MANAGED_3D_VIEWPORT_BOUNDS_ATTR

    first_scene = page_scenes[0]
    page_count = len(page_scenes)
    figure = Figure(
        figsize=figsize
        or (
            max(4.6, first_scene.width * 0.95),
            max(2.1, first_scene.height * 0.72) * page_count,
        )
    )
    FigureCanvasAgg(figure)
    figure.patch.set_facecolor(first_scene.style.theme.figure_facecolor)
    top = 0.98
    bottom = 0.02
    left = 0.02
    width = 0.96
    total_height = top - bottom
    gap = 0.02
    subplot_height = (total_height - (gap * max(0, page_count - 1))) / float(page_count)

    for page_index, page_scene in enumerate(page_scenes):
        subplot_bottom = bottom + ((page_count - page_index - 1) * (subplot_height + gap))
        axes = figure.add_axes((left, subplot_bottom, width, subplot_height), projection="3d")
        pipeline_bounds = (left, subplot_bottom, width, subplot_height)
        setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, pipeline_bounds)
        renderer.render(page_scene, ax=axes)

    save_rendered_figure(figure, output)


def _render_draw_pipeline_on_axes(
    pipeline: PreparedDrawPipeline,
    *,
    axes: Axes,
    output: OutputPath | None,
) -> Axes:
    from ._draw_managed import render_draw_pipeline_on_axes

    return render_draw_pipeline_on_axes(
        pipeline,
        axes=axes,
        output=output,
    )


def _is_3d_axes(ax: Axes) -> bool:
    from ._draw_managed import is_3d_axes

    return is_3d_axes(ax)
