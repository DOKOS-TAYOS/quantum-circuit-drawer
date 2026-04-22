"""Private managed-render pipeline helpers for 2D and 3D drawing."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, TypeGuard, cast

from ..drawing.pipeline import PreparedDrawPipeline
from ..renderers._render_support import should_use_managed_agg_canvas, show_figure_if_supported
from ..style import DrawStyle
from ..style.defaults import replace_draw_style, resolved_line_width, uses_default_line_width
from ..typing import LayoutEngineLike, OutputPath
from .controls import apply_managed_3d_axes_bounds as _apply_managed_3d_axes_bounds_impl
from .page_window import apply_page_window_axes_bounds as _apply_page_window_axes_bounds_impl
from .page_window import configure_page_window as _configure_page_window_impl
from .slider_2d import _DEFAULT_VISIBLE_QUBITS, _visible_qubits_viewport_height
from .slider_2d import configure_page_slider as _configure_page_slider_impl
from .slider_2d import page_slider_figsize as _page_slider_figsize_impl
from .slider_3d import configure_3d_page_slider as _configure_3d_page_slider_impl
from .topology_menu import attach_topology_menu
from .viewport import axes_viewport_pixels
from .viewport import page_window_adaptive_paged_scene as _page_window_adaptive_paged_scene_impl
from .viewport import viewport_adaptive_paged_scene as _viewport_adaptive_paged_scene_impl

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ..layout.scene import LayoutScene
    from ..layout.scene_3d import LayoutScene3D
    from ..renderers.matplotlib_renderer import MatplotlibRenderer

_ADAPTIVE_LINE_WIDTH_REFERENCE_PIXELS_PER_UNIT = 96.0
_ADAPTIVE_LINE_WIDTH_MIN = 0.75
_ADAPTIVE_LINE_WIDTH_MAX = 2.4
logger = logging.getLogger(__name__)


def render_managed_draw_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
    respect_precomputed_scene: bool = False,
) -> tuple[Figure, Axes]:
    """Render a prepared pipeline on a managed figure."""

    from ..renderers._matplotlib_figure import (
        clear_topology_menu_state,
        create_managed_figure,
        set_page_slider,
        set_page_window,
    )

    hover_enabled = (
        pipeline.paged_scene.hover_enabled
        if is_3d_scene(pipeline.paged_scene)
        else cast("LayoutScene", pipeline.paged_scene).hover.enabled
    )
    use_agg_canvas = should_use_managed_agg_canvas(
        show=show,
        output=output,
        prefer_offscreen_when_hidden=not hover_enabled,
    )

    if is_3d_scene(pipeline.paged_scene):
        scene_3d = pipeline.paged_scene
        figure_width, figure_height = figsize or (
            max(4.6, scene_3d.width * 0.95),
            max(2.1, scene_3d.height * 0.72),
        )
        figure, axes = create_managed_figure(
            scene_3d,
            figure_width=figure_width,
            figure_height=figure_height,
            use_agg=use_agg_canvas,
            projection="3d",
        )
        clear_topology_menu_state(figure)
        if output is not None and page_slider:
            pipeline.renderer.render(scene_3d, ax=axes, output=output)
            axes.clear()
            output = None

        page_slider_state = None
        if page_slider:
            page_slider_state = _configure_3d_page_slider_impl(
                figure=figure,
                axes=axes,
                pipeline=pipeline,
                set_page_slider=set_page_slider,
            )

        if pipeline.draw_options.topology_menu and output is None and not use_agg_canvas:
            attach_topology_menu(figure=figure, axes=axes, pipeline=pipeline)
        else:
            _apply_managed_3d_axes_bounds_impl(axes, has_page_slider=page_slider_state is not None)

        scene_to_render = scene_3d if page_slider_state is None else page_slider_state.current_scene
        pipeline.renderer.render(scene_to_render, ax=axes, output=output)
        logger.debug(
            "Rendered managed 3D figure%s",
            " with page slider" if page_slider_state is not None else " without page slider",
        )
        show_figure_if_supported(figure, show=show)
        return figure, axes

    if page_slider:
        scene_2d = cast("LayoutScene", pipeline.paged_scene)
        layout_engine = cast(LayoutEngineLike, pipeline.layout_engine)
        resolved_visible_qubits = min(
            max(1, 1 if not scene_2d.wires else _DEFAULT_VISIBLE_QUBITS),
            len(scene_2d.wires),
        )
        initial_viewport_height = _visible_qubits_viewport_height(
            scene_2d,
            visible_qubits=resolved_visible_qubits,
        )
        first_page = scene_2d.pages[0]
        initial_viewport_width = min(
            scene_2d.width,
            scene_2d.style.margin_left
            + max(first_page.content_width, scene_2d.style.max_page_width)
            + scene_2d.style.margin_right,
        )
        figure_width, figure_height = _page_slider_figsize_impl(
            initial_viewport_width,
            initial_viewport_height,
        )
        if figsize is not None:
            figure_width, figure_height = figsize
        else:
            figure_width = min(11.0, figure_width)
            figure_height = min(7.0, figure_height)
        figure, axes = create_managed_figure(
            scene_2d,
            figure_width=figure_width,
            figure_height=figure_height,
            use_agg=use_agg_canvas,
        )
        frozen_style = _freeze_default_line_width_for_scene(
            style=scene_2d.style,
            scene=scene_2d,
            axes=axes,
        )
        scene_2d.style = replace_draw_style(
            scene_2d.style,
            line_width=resolved_line_width(frozen_style),
        )
        if output is not None:
            pipeline.renderer.render(scene_2d, ax=axes, output=output)
            axes.clear()
        _configure_page_slider_impl(
            figure=figure,
            axes=axes,
            scene=scene_2d,
            viewport_width=initial_viewport_width,
            set_page_slider=set_page_slider,
            viewport_height=initial_viewport_height,
            quantum_wire_count=len(pipeline.ir.quantum_wires),
            allow_figure_resize=figsize is None,
            circuit=pipeline.ir,
            layout_engine=layout_engine,
            renderer=cast("MatplotlibRenderer", pipeline.renderer),
            normalized_style=frozen_style,
        )
        logger.debug(
            "Rendered managed figure with discrete page slider viewport_width=%.2f viewport_height=%.2f pages=%d",
            initial_viewport_width,
            initial_viewport_height,
            len(scene_2d.pages),
        )
    elif page_window:
        scene_2d = cast("LayoutScene", pipeline.paged_scene)
        figure_width, figure_height = figsize or (
            max(4.6, scene_2d.width * 0.95),
            max(2.1, scene_2d.page_height * 0.72) + 1.0,
        )
        figure, axes = create_managed_figure(
            scene_2d,
            figure_width=figure_width,
            figure_height=figure_height,
            use_agg=use_agg_canvas,
        )
        _apply_page_window_axes_bounds_impl(axes)
        from . import drawing as drawing_facade

        page_window_scene_builder = getattr(
            drawing_facade,
            "page_window_adaptive_paged_scene",
            _page_window_adaptive_paged_scene_impl,
        )
        initial_scene, effective_page_width = page_window_scene_builder(
            pipeline.ir,
            cast(LayoutEngineLike, pipeline.layout_engine),
            scene_2d.style,
            axes,
            hover_enabled=scene_2d.hover.enabled,
            initial_scene=scene_2d,
            visible_page_count=1,
        )
        frozen_style = _freeze_default_line_width_for_scene(
            style=initial_scene.style,
            scene=initial_scene,
            axes=axes,
        )
        initial_scene.style = frozen_style
        if output is not None:
            pipeline.renderer.render(initial_scene, ax=axes, output=output)
            axes.clear()
        _configure_page_window_impl(
            figure=figure,
            axes=axes,
            circuit=pipeline.ir,
            layout_engine=cast(LayoutEngineLike, pipeline.layout_engine),
            renderer=cast("MatplotlibRenderer", pipeline.renderer),
            scene=initial_scene,
            effective_page_width=effective_page_width,
            set_page_window=set_page_window,
        )
        logger.debug(
            "Rendered managed figure with fixed page window effective_page_width=%.2f pages=%d",
            effective_page_width,
            len(initial_scene.pages),
        )
    else:
        scene_2d = cast("LayoutScene", pipeline.paged_scene)
        figure_width, figure_height = figsize or (
            max(4.6, scene_2d.width * 0.95),
            max(2.1, scene_2d.page_height * 0.72),
        )
        figure, axes = create_managed_figure(
            scene_2d,
            figure_width=figure_width,
            figure_height=figure_height,
            use_agg=use_agg_canvas,
        )
        render_draw_pipeline_on_axes(
            pipeline,
            axes=axes,
            output=output,
            respect_precomputed_scene=respect_precomputed_scene,
        )
        logger.debug("Rendered managed figure without page slider")

    show_figure_if_supported(figure, show=show)
    return figure, axes


def render_draw_pipeline_on_axes(
    pipeline: PreparedDrawPipeline,
    *,
    axes: Axes,
    output: OutputPath | None,
    respect_precomputed_scene: bool = False,
) -> Axes:
    """Render a prepared pipeline on existing axes using one-shot 2D composition."""

    from ..renderers._matplotlib_figure import clear_text_scaling_state, set_viewport_width

    clear_text_scaling_state(axes)

    if is_3d_scene(pipeline.paged_scene):
        axes.clear()
        pipeline.renderer.render(pipeline.paged_scene, ax=axes, output=output)
        return axes

    prepared_scene = cast("LayoutScene", pipeline.paged_scene)
    if respect_precomputed_scene:
        scene_2d = prepared_scene
    else:
        from . import drawing as drawing_facade

        viewport_scene_builder = getattr(
            drawing_facade,
            "viewport_adaptive_paged_scene",
            _viewport_adaptive_paged_scene_impl,
        )
        scene_2d, _ = viewport_scene_builder(
            pipeline.ir,
            cast(LayoutEngineLike, pipeline.layout_engine),
            pipeline.normalized_style,
            axes,
            hover_enabled=prepared_scene.hover.enabled,
            initial_scene=prepared_scene,
        )
        scene_2d.hover = prepared_scene.hover
    frozen_style = _freeze_default_line_width_for_scene(
        style=scene_2d.style,
        scene=scene_2d,
        axes=axes,
    )
    scene_2d.style = frozen_style
    axes.clear()
    pipeline.renderer.render(scene_2d, ax=axes, output=output)
    set_viewport_width(axes.figure, viewport_width=scene_2d.width)
    return axes


def is_3d_scene(scene: LayoutScene | LayoutScene3D) -> TypeGuard[LayoutScene3D]:
    """Return whether a prepared scene is a 3D scene."""

    return hasattr(scene, "depth")


def _freeze_default_line_width_for_scene(
    *,
    style: DrawStyle,
    scene: LayoutScene,
    axes: Axes,
) -> DrawStyle:
    """Resolve and freeze the initial adaptive 2D line width for one scene."""

    if not uses_default_line_width(style):
        return style

    resolved_width = _adaptive_default_line_width(
        style=style,
        scene=scene,
        axes=axes,
    )
    return replace_draw_style(style, line_width=resolved_width)


def _adaptive_default_line_width(
    *,
    style: DrawStyle,
    scene: LayoutScene,
    axes: Axes,
) -> float:
    """Scale the default 2D line width to the scene density visible in the viewport."""

    viewport_width_pixels, viewport_height_pixels = axes_viewport_pixels(axes)
    if (
        viewport_width_pixels <= 0.0
        or viewport_height_pixels <= 0.0
        or scene.width <= 0.0
        or scene.height <= 0.0
    ):
        return resolved_line_width(style)

    pixels_per_layout_unit_x = viewport_width_pixels / scene.width
    pixels_per_layout_unit_y = viewport_height_pixels / scene.height
    visible_density = math.sqrt(pixels_per_layout_unit_x * pixels_per_layout_unit_y)
    relative_scale = math.sqrt(
        max(0.2, visible_density / _ADAPTIVE_LINE_WIDTH_REFERENCE_PIXELS_PER_UNIT)
    )
    scaled_line_width = resolved_line_width(style) * relative_scale
    return min(
        _ADAPTIVE_LINE_WIDTH_MAX,
        max(_ADAPTIVE_LINE_WIDTH_MIN, scaled_line_width),
    )
