"""Managed-figure rendering helpers for the public drawing API."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeGuard, cast

from ._draw_managed_slider import (
    configure_page_slider as _configure_page_slider_impl,
)
from ._draw_managed_slider import (
    page_slider_figsize as _page_slider_figsize_impl,
)
from ._draw_managed_slider import (
    set_slider_view as _set_slider_view_impl,
)
from ._draw_managed_slider import (
    slider_viewport_width as _slider_viewport_width_impl,
)
from ._draw_managed_viewport import (
    auto_paging_matches as _auto_paging_matches_impl,
)
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
    scene_aspect_ratio as _scene_aspect_ratio_impl,
)
from ._draw_managed_viewport import (
    viewport_adaptive_paged_scene as _viewport_adaptive_paged_scene_impl,
)
from ._draw_managed_viewport import (
    viewport_scene_score as _viewport_scene_score_impl,
)
from ._draw_managed_viewport import (
    viewport_signature as _viewport_signature_impl,
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
from .typing import LayoutEngineLike, OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D

_PAGE_SLIDER_MAIN_AXES_BOTTOM = 0.18
_MANAGED_3D_VIEWPORT_BOUNDS_ATTR = "_quantum_circuit_drawer_managed_3d_viewport_bounds"
logger = logging.getLogger(__name__)


def render_managed_draw_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
) -> tuple[Figure, Axes]:
    """Render a prepared pipeline on a managed figure."""

    from .renderers._matplotlib_figure import (
        create_managed_figure,
        set_page_slider,
        set_viewport_width,
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
        setattr(axes, _MANAGED_3D_VIEWPORT_BOUNDS_ATTR, (0.0, 0.0, 1.0, 1.0))
        pipeline.renderer.render(scene_3d, ax=axes, output=output)
        logger.debug("Rendered managed 3D figure without page slider")
        show_figure_if_supported(figure, show=show)
        return figure, axes

    if page_slider:
        scene_2d = cast("LayoutScene", pipeline.paged_scene)
        layout_engine = cast(LayoutEngineLike, pipeline.layout_engine)
        slider_scene = build_continuous_slider_scene(
            pipeline.ir,
            layout_engine,
            pipeline.normalized_style,
            hover_enabled=scene_2d.hover.enabled,
        )
        slider_scene.hover = scene_2d.hover
        initial_viewport_width = min(scene_2d.width, slider_scene.width)
        figure_width, figure_height = page_slider_figsize(
            initial_viewport_width,
            slider_scene.height,
        )
        if figsize is not None:
            figure_width, figure_height = figsize
        if output is None:
            figure, axes = create_managed_figure(
                slider_scene,
                figure_width=figure_width,
                figure_height=figure_height,
                use_agg=use_agg_canvas,
            )
        else:
            figure, axes = create_managed_figure(
                scene_2d,
                figure_width=figure_width,
                figure_height=figure_height,
                use_agg=use_agg_canvas,
            )
            pipeline.renderer.render(scene_2d, ax=axes, output=output)
            axes.clear()
        figure.subplots_adjust(bottom=_PAGE_SLIDER_MAIN_AXES_BOTTOM)
        viewport_width = slider_viewport_width(axes, slider_scene)
        set_viewport_width(figure, viewport_width=viewport_width)
        pipeline.renderer.render(slider_scene, ax=axes)
        configure_page_slider(
            figure=figure,
            axes=axes,
            scene=slider_scene,
            viewport_width=viewport_width,
            set_page_slider=set_page_slider,
        )
        logger.debug(
            "Rendered managed figure with page slider viewport_width=%.2f pages=%d",
            viewport_width,
            len(scene_2d.pages),
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
            enable_auto_paging=True,
            reconcile_on_first_draw=True,
        )
        logger.debug("Rendered managed figure without page slider")

    show_figure_if_supported(figure, show=show)
    return figure, axes


def render_draw_pipeline_on_axes(
    pipeline: PreparedDrawPipeline,
    *,
    axes: Axes,
    output: OutputPath | None,
    enable_auto_paging: bool,
    reconcile_on_first_draw: bool = False,
) -> Axes:
    """Render a prepared pipeline on existing 2D axes, with optional auto paging."""

    from .renderers._matplotlib_figure import (
        AutoPagingState,
        clear_auto_paging_state,
        clear_text_scaling_state,
        set_auto_paging_state,
        set_viewport_width,
    )

    clear_auto_paging_state(axes)
    clear_text_scaling_state(axes)

    if is_3d_scene(pipeline.paged_scene) or not enable_auto_paging:
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
    )
    scene_2d.hover = prepared_scene.hover
    axes.clear()
    pipeline.renderer.render(scene_2d, ax=axes, output=output)
    set_viewport_width(axes.figure, viewport_width=scene_2d.width)
    configure_zoom_text_scaling(axes, scene=scene_2d)

    auto_paging_state = AutoPagingState(
        ir=pipeline.ir,
        layout_engine=cast(LayoutEngineLike, pipeline.layout_engine),
        renderer=pipeline.renderer,
        normalized_style=pipeline.normalized_style,
        scene=scene_2d,
        effective_page_width=effective_page_width,
        hover_enabled=prepared_scene.hover.enabled,
        last_viewport_signature=viewport_signature(axes),
        needs_initial_draw_reconcile=reconcile_on_first_draw,
    )
    set_auto_paging_state(axes, auto_paging_state)
    configure_auto_paging(axes, auto_paging_state)
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
) -> tuple[LayoutScene, float]:
    """Return the paged scene whose aspect best matches the current axes viewport."""

    return _viewport_adaptive_paged_scene_impl(
        circuit,
        layout_engine,
        style,
        axes,
        hover_enabled=hover_enabled,
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


def configure_auto_paging(axes: Axes, state: object) -> None:
    """Attach resize-aware paging callbacks to the provided axes."""

    from matplotlib.backend_bases import Event

    from .renderers._matplotlib_figure import (
        AutoPagingState,
        get_auto_paging_state,
        set_viewport_width,
    )

    if not isinstance(state, AutoPagingState):
        return

    canvas = axes.figure.canvas
    if canvas is None:
        return

    def request_redraw(_event: Event) -> None:
        if state.is_updating:
            return
        canvas.draw_idle()

    def redraw_if_needed(_event: Event) -> None:
        current_state = get_auto_paging_state(axes)
        if current_state is None or current_state is not state or state.is_updating:
            return

        current_signature = viewport_signature(axes)
        if current_signature is None:
            return
        if (
            not state.needs_initial_draw_reconcile
            and current_signature == state.last_viewport_signature
        ):
            return

        candidate_scene, candidate_page_width = viewport_adaptive_paged_scene(
            state.ir,
            state.layout_engine,
            state.normalized_style,
            axes,
            hover_enabled=state.hover_enabled,
        )
        candidate_scene.hover = state.scene.hover
        state.last_viewport_signature = current_signature
        state.needs_initial_draw_reconcile = False
        if auto_paging_matches(
            current_state=state,
            candidate_scene=candidate_scene,
            candidate_page_width=candidate_page_width,
        ):
            return

        state.is_updating = True
        try:
            axes.clear()
            state.renderer.render(candidate_scene, ax=axes)
            set_viewport_width(axes.figure, viewport_width=candidate_scene.width)
            configure_zoom_text_scaling(axes, scene=candidate_scene)
            state.scene = candidate_scene
            state.effective_page_width = candidate_page_width
        finally:
            state.is_updating = False
        canvas.draw_idle()

    state.resize_callback_id = canvas.mpl_connect("resize_event", request_redraw)
    state.draw_callback_id = canvas.mpl_connect("draw_event", redraw_if_needed)


def auto_paging_matches(
    *,
    current_state: object,
    candidate_scene: LayoutScene,
    candidate_page_width: float,
) -> bool:
    """Return whether a candidate scene would keep the current paging unchanged."""

    return _auto_paging_matches_impl(
        current_state=current_state,
        candidate_scene=candidate_scene,
        candidate_page_width=candidate_page_width,
    )


def viewport_signature(axes: Axes) -> tuple[int, int] | None:
    """Return an integer pixel signature for the current visible axes viewport."""

    return _viewport_signature_impl(axes)


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
) -> None:
    """Attach and wire a slider that scrolls the rendered circuit horizontally."""

    _configure_page_slider_impl(
        figure=figure,
        axes=axes,
        scene=scene,
        viewport_width=viewport_width,
        set_page_slider=set_page_slider,
    )


def page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    """Return a readable managed figure size for page-slider mode."""

    return _page_slider_figsize_impl(viewport_width, scene_height)


def slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene width for the current axes aspect ratio."""

    return _slider_viewport_width_impl(axes, scene)


def set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
) -> None:
    """Set the 2D axes limits used for the slider viewport."""

    _set_slider_view_impl(axes, scene, x_offset=x_offset, viewport_width=viewport_width)


def is_3d_axes(ax: Axes) -> bool:
    """Return whether the provided axes is a Matplotlib 3D axes."""

    return getattr(ax, "name", "") == "3d"


def is_3d_scene(scene: LayoutScene | LayoutScene3D) -> TypeGuard[LayoutScene3D]:
    """Return whether a prepared scene is a 3D scene."""

    return hasattr(scene, "depth")
