"""Managed-figure rendering helpers for the public drawing API."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeGuard, cast

from ._draw_managed_page_window import (
    apply_page_window_axes_bounds as _apply_page_window_axes_bounds_impl,
)
from ._draw_managed_page_window import (
    configure_page_window as _configure_page_window_impl,
)
from ._draw_managed_slider import (
    _DEFAULT_VISIBLE_QUBITS,
    _visible_qubits_viewport_height,
)
from ._draw_managed_slider import (
    apply_managed_3d_axes_bounds as _apply_managed_3d_axes_bounds_impl,
)
from ._draw_managed_slider import (
    configure_3d_page_slider as _configure_3d_page_slider_impl,
)
from ._draw_managed_slider import (
    configure_page_slider as _configure_page_slider_impl,
)
from ._draw_managed_slider import (
    page_slider_figsize as _page_slider_figsize_impl,
)
from ._draw_managed_slider import (
    prepare_page_slider_layout as _prepare_page_slider_layout_impl,
)
from ._draw_managed_slider import (
    set_slider_view as _set_slider_view_impl,
)
from ._draw_managed_slider import (
    slider_viewport_height as _slider_viewport_height_impl,
)
from ._draw_managed_slider import (
    slider_viewport_width as _slider_viewport_width_impl,
)
from ._draw_managed_topology_menu import attach_topology_menu
from ._draw_managed_viewport import (
    axes_viewport_pixels as _axes_viewport_pixels_impl,
)
from ._draw_managed_viewport import (
    axes_viewport_ratio as _axes_viewport_ratio_impl,
)
from ._draw_managed_viewport import (
    build_continuous_slider_scene as _build_continuous_slider_scene_impl,
)
from ._draw_managed_viewport import (
    compute_paged_scene as _compute_paged_scene_impl,
)
from ._draw_managed_viewport import (
    page_window_adaptive_paged_scene as _page_window_adaptive_paged_scene_impl,
)
from ._draw_managed_viewport import (
    scene_aspect_ratio as _scene_aspect_ratio_impl,
)
from ._draw_managed_viewport import (
    viewport_adaptive_paged_scene as _viewport_adaptive_paged_scene_impl,
)
from ._draw_managed_viewport import (
    viewport_scene_score as _viewport_scene_score_impl,
)
from ._draw_managed_zoom import (
    configure_zoom_text_scaling as _configure_zoom_text_scaling_impl,
)
from ._draw_managed_zoom import (
    current_text_scale as _current_text_scale_impl,
)
from ._draw_managed_zoom import (
    current_view_size as _current_view_size_impl,
)
from ._draw_pipeline import PreparedDrawPipeline
from .renderers._render_support import should_use_managed_agg_canvas, show_figure_if_supported
from .style import DrawStyle
from .style.defaults import replace_draw_style, resolved_line_width, uses_default_line_width
from .typing import LayoutEngineLike, OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ._draw_managed_slider import Managed2DSliderLayout, Managed3DPageSliderState
    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D
    from .renderers.matplotlib_renderer import MatplotlibRenderer

_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
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
) -> tuple[Figure, Axes]:
    """Render a prepared pipeline on a managed figure."""

    from .renderers._matplotlib_figure import (
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
            page_slider_state = cast(
                "Managed3DPageSliderState | None",
                configure_3d_page_slider(
                    figure=figure,
                    axes=axes,
                    pipeline=pipeline,
                    set_page_slider=set_page_slider,
                ),
            )

        if pipeline.draw_options.topology_menu and output is None and not use_agg_canvas:
            attach_topology_menu(figure=figure, axes=axes, pipeline=pipeline)
        else:
            apply_managed_3d_axes_bounds(axes, has_page_slider=page_slider_state is not None)

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
            max(1, 1 if not scene_2d.wires else _DEFAULT_VISIBLE_QUBITS), len(scene_2d.wires)
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
        figure_width, figure_height = page_slider_figsize(
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
            scene_2d.style, line_width=resolved_line_width(frozen_style)
        )
        if output is not None:
            pipeline.renderer.render(scene_2d, ax=axes, output=output)
            axes.clear()
        configure_page_slider(
            figure=figure,
            axes=axes,
            scene=scene_2d,
            viewport_width=initial_viewport_width,
            viewport_height=initial_viewport_height,
            quantum_wire_count=len(pipeline.ir.quantum_wires),
            allow_figure_resize=figsize is None,
            set_page_slider=set_page_slider,
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
        initial_scene, effective_page_width = page_window_adaptive_paged_scene(
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
        configure_page_window(
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
        )
        logger.debug("Rendered managed figure without page slider")

    show_figure_if_supported(figure, show=show)
    return figure, axes


def render_draw_pipeline_on_axes(
    pipeline: PreparedDrawPipeline,
    *,
    axes: Axes,
    output: OutputPath | None,
) -> Axes:
    """Render a prepared pipeline on existing axes using one-shot 2D composition."""

    from .renderers._matplotlib_figure import clear_text_scaling_state, set_viewport_width

    clear_text_scaling_state(axes)

    if is_3d_scene(pipeline.paged_scene):
        axes.clear()
        pipeline.renderer.render(pipeline.paged_scene, ax=axes, output=output)
        return axes

    prepared_scene = cast("LayoutScene", pipeline.paged_scene)
    scene_2d, effective_page_width = viewport_adaptive_paged_scene(
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


def build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a continuous-width 2D scene for page-slider mode."""

    return _build_continuous_slider_scene_impl(
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

    return _viewport_adaptive_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
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
    """Return the paged scene that best matches the fixed page-window viewport."""

    return _page_window_adaptive_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
        initial_scene=initial_scene,
        visible_page_count=visible_page_count,
    )


def compute_paged_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
    *,
    hover_enabled: bool = True,
) -> LayoutScene:
    """Compute a paged 2D scene using the provided normalized style."""

    return _compute_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        hover_enabled=hover_enabled,
    )


def axes_viewport_ratio(axes: Axes) -> float:
    """Return the current visible axes aspect ratio in pixels."""

    return _axes_viewport_ratio_impl(axes)


def axes_viewport_pixels(axes: Axes) -> tuple[float, float]:
    """Return the current axes viewport size in pixels."""

    return _axes_viewport_pixels_impl(axes)


def scene_aspect_ratio(scene: LayoutScene) -> float:
    """Return the width-to-height ratio of a 2D scene."""

    return _scene_aspect_ratio_impl(scene)


def viewport_scene_score(scene: LayoutScene, viewport_ratio: float) -> float:
    """Return how closely the scene aspect matches the viewport aspect."""

    return _viewport_scene_score_impl(scene, viewport_ratio)


def configure_zoom_text_scaling(axes: Axes, *, scene: LayoutScene) -> None:
    """Attach zoom-responsive text scaling to the provided 2D axes."""

    _configure_zoom_text_scaling_impl(axes, scene=scene)


def current_view_size(axes: Axes) -> tuple[float, float]:
    """Return the current visible data window for the axes."""

    return _current_view_size_impl(axes)


def current_text_scale(axes: Axes, state: object) -> float:
    """Return the current zoom scale factor for 2D text."""

    return _current_text_scale_impl(axes, state)


def configure_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
    set_page_slider: Callable[[Figure, object], None],
    viewport_height: float | None = None,
    layout: object | None = None,
    quantum_wire_count: int | None = None,
    allow_figure_resize: bool = True,
    circuit: CircuitIR | None = None,
    layout_engine: LayoutEngineLike | None = None,
    renderer: MatplotlibRenderer | None = None,
    normalized_style: DrawStyle | None = None,
) -> None:
    """Attach and wire a slider that redraws discrete 2D circuit windows."""

    _configure_page_slider_impl(
        figure=figure,
        axes=axes,
        scene=scene,
        viewport_width=viewport_width,
        set_page_slider=set_page_slider,
        viewport_height=viewport_height,
        layout=cast("Managed2DSliderLayout | None", layout),
        quantum_wire_count=quantum_wire_count,
        allow_figure_resize=allow_figure_resize,
        circuit=circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        normalized_style=normalized_style,
    )


def configure_page_window(
    *,
    figure: Figure,
    axes: Axes,
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    renderer: MatplotlibRenderer,
    scene: LayoutScene,
    effective_page_width: float,
    set_page_window: Callable[[Figure, object], None],
) -> object:
    """Attach fixed page-window controls for one managed 2D figure."""

    return _configure_page_window_impl(
        figure=figure,
        axes=axes,
        circuit=circuit,
        layout_engine=layout_engine,
        renderer=renderer,
        scene=scene,
        effective_page_width=effective_page_width,
        set_page_window=set_page_window,
    )


def page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    """Return a readable managed figure size for page-slider mode."""

    return _page_slider_figsize_impl(viewport_width, scene_height)


def slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene width for the current axes aspect ratio."""

    return _slider_viewport_width_impl(axes, scene)


def slider_viewport_height(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene height for the current axes aspect ratio."""

    return _slider_viewport_height_impl(axes, scene)


def set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
    y_offset: float = 0.0,
    viewport_height: float | None = None,
) -> None:
    """Set the 2D axes limits used for the slider viewport."""

    _set_slider_view_impl(
        axes,
        scene,
        x_offset=x_offset,
        y_offset=y_offset,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )


def configure_3d_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    pipeline: PreparedDrawPipeline,
    set_page_slider: Callable[[Figure, object], None],
) -> object | None:
    """Attach and wire a 3D page slider that moves through circuit columns."""

    return _configure_3d_page_slider_impl(
        figure=figure,
        axes=axes,
        pipeline=pipeline,
        set_page_slider=set_page_slider,
    )


def prepare_page_slider_layout(axes: Axes, scene: LayoutScene) -> object:
    """Resolve the 2D slider layout and viewport before rendering."""

    return _prepare_page_slider_layout_impl(axes, scene)


def apply_managed_3d_axes_bounds(
    axes: Axes, *, has_page_slider: bool
) -> tuple[float, float, float, float]:
    """Apply managed 3D viewport bounds for the active control layout."""

    return _apply_managed_3d_axes_bounds_impl(axes, has_page_slider=has_page_slider)


def is_3d_axes(ax: Axes) -> bool:
    """Return whether the provided axes is a Matplotlib 3D axes."""

    return getattr(ax, "name", "") == "3d"


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

    resolved_line_width = _adaptive_default_line_width(
        style=style,
        scene=scene,
        axes=axes,
    )
    return replace_draw_style(style, line_width=resolved_line_width)


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
