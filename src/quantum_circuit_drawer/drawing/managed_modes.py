"""Managed-render dispatch helpers for public draw orchestration."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from ..config import DrawMode
from ..diagnostics import RenderDiagnostic
from ..managed.rendering import (
    is_3d_axes,
    render_draw_pipeline_on_axes,
    render_managed_draw_pipeline,
)
from ..result import DrawResult
from .pages import single_page_scenes
from .results import build_draw_result

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..layout.scene import LayoutScene
    from ..layout.scene_3d import LayoutScene3D
    from ..renderers.base import BaseRenderer
    from ..typing import LayoutEngineLike, OutputPath
    from .pipeline import PreparedDrawPipeline
    from .preparation import PreparedDrawCall

logger = logging.getLogger(__name__)


def draw_result_from_prepared_call(
    prepared: PreparedDrawCall,
    *,
    defer_show: bool = False,
) -> DrawResult:
    """Execute one prepared draw call and return the public result object."""

    resolved_config = prepared.resolved_config
    request = prepared.request
    pipeline = prepared.pipeline

    if request.ax is None:
        if resolved_config.mode is DrawMode.PAGES and request.pipeline_options.view == "2d":
            return _render_managed_2d_pages_result(
                pipeline,
                output=request.output,
                show=request.show,
                defer_show=defer_show,
                figsize=request.figsize,
                page_slider=request.page_slider,
                page_window=request.page_window,
                mode=resolved_config.mode,
                diagnostics=prepared.diagnostics,
            )
        if resolved_config.mode is DrawMode.PAGES and request.pipeline_options.view == "3d":
            return _render_managed_3d_pages_result(
                pipeline,
                output=request.output,
                show=request.show,
                defer_show=defer_show,
                figsize=request.figsize,
                mode=resolved_config.mode,
                diagnostics=prepared.diagnostics,
            )
        if (
            resolved_config.mode is DrawMode.PAGES_CONTROLS
            and request.pipeline_options.view == "3d"
        ):
            return _render_managed_3d_page_controls_result(
                pipeline,
                output=request.output,
                show=request.show,
                defer_show=defer_show,
                figsize=request.figsize,
                mode=resolved_config.mode,
                diagnostics=prepared.diagnostics,
            )
        figure, axes = render_managed_draw_pipeline(
            pipeline,
            output=request.output,
            show=request.show,
            call_show=request.show and not defer_show,
            figsize=request.figsize,
            page_slider=request.page_slider,
            page_window=request.page_window,
        )
        return build_draw_result(
            primary_figure=figure,
            primary_axes=axes,
            figures=(figure,),
            axes=(axes,),
            mode=resolved_config.mode,
            page_count=page_count_for_pipeline(pipeline, mode=resolved_config.mode),
            diagnostics=prepared.diagnostics,
            pipeline=pipeline,
            output=request.output,
        )

    if request.pipeline_options.view == "3d" and not is_3d_axes(request.ax):
        raise ValueError("view='3d' requires a 3D Matplotlib axes")
    logger.debug("Rendering scene on caller-managed Matplotlib axes")
    axes = render_draw_pipeline_on_axes(
        pipeline,
        axes=request.ax,
        output=request.output,
    )
    figure = cast("Figure", axes.figure)
    return build_draw_result(
        primary_figure=figure,
        primary_axes=axes,
        figures=(figure,),
        axes=(axes,),
        mode=resolved_config.mode,
        page_count=page_count_for_pipeline(pipeline, mode=resolved_config.mode),
        diagnostics=prepared.diagnostics,
        pipeline=pipeline,
        output=request.output,
    )


def page_count_for_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    mode: DrawMode,
) -> int:
    """Return the number of pages represented by one prepared pipeline."""

    if pipeline.draw_options.view != "3d":
        return len(getattr(pipeline.paged_scene, "pages", ()) or ())
    if mode is DrawMode.FULL:
        return 1
    return len(_windowed_3d_scenes(pipeline))


def _render_managed_2d_pages_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    defer_show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
    mode: DrawMode,
    diagnostics: tuple[RenderDiagnostic, ...],
) -> DrawResult:
    from ..renderers._render_support import close_figure_best_effort

    adapted_scene = _page_window_adapted_2d_scene(pipeline, figsize=figsize)
    adapted_pipeline = replace(pipeline, paged_scene=adapted_scene)
    page_scenes = single_page_scenes(adapted_scene)

    if output is not None:
        saved_figure, _ = render_managed_draw_pipeline(
            adapted_pipeline,
            output=output,
            show=False,
            figsize=figsize,
            page_slider=page_slider,
            page_window=page_window,
        )
        close_figure_best_effort(
            saved_figure,
            logger=logger,
            context="managed 2D pages saved figure best-effort cleanup",
        )

    figures: list[Figure] = []
    axes_list: list[Axes] = []
    for page_index, _page_scene in enumerate(page_scenes):
        figure, axes = render_managed_draw_pipeline(
            adapted_pipeline,
            output=None,
            show=show,
            call_show=show and not defer_show,
            figsize=figsize,
            page_slider=False,
            page_window=True,
            respect_precomputed_scene=True,
            attach_page_window_controls=False,
            page_window_initial_start_page=page_index,
        )
        figures.append(figure)
        axes_list.append(axes)

    return build_draw_result(
        primary_figure=figures[0],
        primary_axes=axes_list[0],
        figures=tuple(figures),
        axes=tuple(axes_list),
        mode=mode,
        page_count=len(page_scenes),
        diagnostics=diagnostics,
        pipeline=pipeline,
        output=output,
    )


def _render_managed_3d_pages_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    defer_show: bool,
    figsize: tuple[float, float] | None,
    mode: DrawMode,
    diagnostics: tuple[RenderDiagnostic, ...],
) -> DrawResult:
    from ..managed.page_window_3d import configure_3d_page_window
    from ..renderers._matplotlib_figure import create_managed_figure, set_page_window
    from ..renderers._render_support import should_use_managed_agg_canvas, show_figure_if_supported

    page_scenes = _windowed_3d_scenes(pipeline, figsize=figsize)

    if output is not None:
        _save_clean_3d_pages_output(
            page_scenes,
            renderer=pipeline.renderer,
            output=output,
            figsize=figsize,
        )

    figures: list[Figure] = []
    axes_list: list[Axes] = []
    for page_index, page_scene in enumerate(page_scenes):
        use_agg_canvas = should_use_managed_agg_canvas(
            show=show,
            output=None,
            prefer_offscreen_when_hidden=not page_scene.hover_enabled,
        )
        figure_width, figure_height = figsize or (
            max(4.6, page_scene.width * 0.95),
            max(2.1, page_scene.height * 0.72),
        )
        figure, axes = create_managed_figure(
            page_scene,
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
            keyboard_shortcuts_enabled=pipeline.draw_options.keyboard_shortcuts,
            double_click_toggle_enabled=pipeline.draw_options.double_click_toggle,
            initial_start_page=page_index,
            attach_controls=False,
        )
        show_figure_if_supported(figure, show=show and not defer_show)
        figures.append(figure)
        axes_list.append(page_window.display_axes[0])

    return build_draw_result(
        primary_figure=figures[0],
        primary_axes=axes_list[0],
        figures=tuple(figures),
        axes=tuple(axes_list),
        mode=mode,
        page_count=len(page_scenes),
        diagnostics=diagnostics,
        pipeline=pipeline,
        output=output,
    )


def _render_managed_3d_page_controls_result(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    defer_show: bool,
    figsize: tuple[float, float] | None,
    mode: DrawMode,
    diagnostics: tuple[RenderDiagnostic, ...],
) -> DrawResult:
    from ..managed.page_window_3d import configure_3d_page_window
    from ..managed.topology_menu import attach_topology_menu
    from ..renderers._matplotlib_figure import create_managed_figure, set_page_window
    from ..renderers._render_support import should_use_managed_agg_canvas, show_figure_if_supported

    page_scenes = _windowed_3d_scenes(pipeline, figsize=figsize)
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
        keyboard_shortcuts_enabled=pipeline.draw_options.keyboard_shortcuts,
        double_click_toggle_enabled=pipeline.draw_options.double_click_toggle,
    )
    primary_axes = page_window.display_axes[0]
    if pipeline.draw_options.topology_menu and not use_agg_canvas:
        attach_topology_menu(figure=figure, axes=primary_axes, pipeline=pipeline)
    show_figure_if_supported(figure, show=show and not defer_show)
    return build_draw_result(
        primary_figure=figure,
        primary_axes=primary_axes,
        figures=(figure,),
        axes=(primary_axes,),
        mode=mode,
        page_count=len(page_scenes),
        diagnostics=diagnostics,
        pipeline=pipeline,
        output=output,
    )


def _page_window_adapted_2d_scene(
    pipeline: PreparedDrawPipeline,
    *,
    figsize: tuple[float, float] | None,
) -> LayoutScene:
    from ..layout.engine import LayoutEngine
    from ..managed.viewport import page_window_adaptive_paged_scene
    from ..renderers._matplotlib_figure import create_managed_figure

    if pipeline.draw_options.view == "2d":
        initial_scene = cast("LayoutScene", pipeline.paged_scene)
        layout_engine = cast("LayoutEngineLike", pipeline.layout_engine)
    else:
        layout_engine = LayoutEngine()
        initial_scene = layout_engine.compute(pipeline.ir, pipeline.normalized_style)
        initial_scene.hover = pipeline.draw_options.hover

    figure_width, figure_height = figsize or (
        max(4.6, initial_scene.width * 0.95),
        max(2.1, initial_scene.page_height * 0.72),
    )
    figure, axes = create_managed_figure(
        initial_scene,
        figure_width=figure_width,
        figure_height=figure_height,
        use_agg=True,
    )
    try:
        adapted_scene, _ = page_window_adaptive_paged_scene(
            pipeline.ir,
            layout_engine,
            pipeline.normalized_style,
            axes,
            hover_enabled=initial_scene.hover.enabled,
            initial_scene=initial_scene,
            visible_page_count=1,
        )
    finally:
        figure.clear()

    adapted_scene.hover = initial_scene.hover
    return adapted_scene


def _windowed_3d_scenes(
    pipeline: PreparedDrawPipeline,
    *,
    figsize: tuple[float, float] | None = None,
) -> tuple[LayoutScene3D, ...]:
    from ..managed.page_window_3d import windowed_3d_page_scenes

    return windowed_3d_page_scenes(pipeline, figure_size=figsize)


def _save_clean_3d_pages_output(
    page_scenes: tuple[LayoutScene3D, ...],
    *,
    renderer: BaseRenderer,
    output: OutputPath,
    figsize: tuple[float, float] | None,
) -> None:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from ..renderers._render_support import save_rendered_figure
    from ..renderers.matplotlib_renderer_3d import _MANAGED_3D_VIEWPORT_BOUNDS_ATTR

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
