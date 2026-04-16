"""Managed-figure rendering helpers for the public drawing API."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, TypeGuard, cast

from ._draw_pipeline import PreparedDrawPipeline
from .renderers._render_support import show_figure_if_supported
from .style import DrawStyle
from .typing import LayoutEngineLike, OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.backend_bases import DrawEvent, ResizeEvent
    from matplotlib.figure import Figure

    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D

_PAGE_SLIDER_MAIN_AXES_BOTTOM = 0.18
_VIEWPORT_SEARCH_STEPS = 10
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
            use_agg=not show,
            projection="3d",
        )
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
                use_agg=not show,
            )
        else:
            figure, axes = create_managed_figure(
                scene_2d,
                figure_width=figure_width,
                figure_height=figure_height,
                use_agg=not show,
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
            use_agg=not show,
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

    scene_2d, effective_page_width = viewport_adaptive_paged_scene(
        pipeline.ir,
        cast(LayoutEngineLike, pipeline.layout_engine),
        pipeline.normalized_style,
        axes,
    )
    scene_2d.hover = cast("LayoutScene", pipeline.paged_scene).hover
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
) -> LayoutScene:
    """Compute a continuous-width 2D scene for page-slider mode."""

    slider_style = replace(style, max_page_width=float("inf"))
    if hasattr(layout_engine, "_compute_with_normalized_style"):
        return layout_engine._compute_with_normalized_style(  # type: ignore[attr-defined]
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
        return layout_engine._compute_with_normalized_style(  # type: ignore[attr-defined]
            circuit,
            style,
        )
    return layout_engine.compute(circuit, style)


def configure_auto_paging(axes: Axes, state: object) -> None:
    """Attach resize-aware paging callbacks to the provided axes."""

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

    def request_redraw(_event: ResizeEvent) -> None:
        if state.is_updating:
            return
        canvas.draw_idle()

    def redraw_if_needed(_event: DrawEvent) -> None:
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
    """Return the current axes viewport size in pixels.

    This uses ``axes.get_position(original=True)`` so viewport estimates are
    based on the subplot slot after ``subplots_adjust``/resize updates, without
    incorporating any draw-time active-position adjustments. Using the original
    box keeps auto-paging and slider viewport math aligned to the same
    normalized layout budget.
    """

    figure = axes.figure
    figure_width, figure_height = figure.get_size_inches()
    axes_position = axes.get_position(original=True)
    viewport_width = figure_width * figure.dpi * axes_position.width
    viewport_height = figure_height * figure.dpi * axes_position.height
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


def configure_zoom_text_scaling(axes: Axes, *, scene: LayoutScene) -> None:
    """Attach zoom-responsive text scaling to the provided 2D axes."""

    from .renderers._matplotlib_figure import (
        TextScalingState,
        get_base_font_size,
        get_gate_text_metadata,
        get_text_scaling_state,
        set_base_font_size,
        set_text_scaling_state,
    )
    from .renderers.matplotlib_primitives import (
        _build_gate_text_fitting_context,
        _fit_gate_text_font_size_with_context,
        _GateTextFittingContext,
    )

    base_view_width, base_view_height = current_view_size(axes)
    if base_view_width <= 0.0 or base_view_height <= 0.0:
        return
    base_gate_text_context = _build_gate_text_fitting_context(axes, scene)

    for text_artist in axes.texts:
        set_base_font_size(text_artist, text_artist.get_fontsize())

    state = get_text_scaling_state(axes)
    if state is None:
        state = TextScalingState(
            base_view_width=base_view_width,
            base_view_height=base_view_height,
            scene=scene,
            base_points_per_layout_unit=base_gate_text_context.points_per_layout_unit,
            last_points_per_layout_unit=base_gate_text_context.points_per_layout_unit,
        )
        set_text_scaling_state(axes, state)
        canvas = axes.figure.canvas

        def apply_text_scale(*, request_redraw: bool) -> None:
            current_state = get_text_scaling_state(axes)
            if current_state is None or current_state is not state or state.is_updating:
                return

            scale_factor = current_text_scale(axes, state)
            if request_redraw:
                gate_text_context = _build_gate_text_fitting_context(axes, current_state.scene)
                points_per_layout_unit = gate_text_context.points_per_layout_unit
            else:
                points_per_layout_unit = state.base_points_per_layout_unit * scale_factor
                gate_text_context = _GateTextFittingContext(
                    default_scale=1.0,
                    points_per_layout_unit=points_per_layout_unit,
                )

            if math.isclose(
                scale_factor,
                state.last_scale_factor,
                rel_tol=1e-6,
                abs_tol=1e-6,
            ) and math.isclose(
                points_per_layout_unit,
                state.last_points_per_layout_unit,
                rel_tol=1e-6,
                abs_tol=1e-6,
            ):
                return

            state.is_updating = True
            try:
                for text_artist in axes.texts:
                    gate_text_metadata = get_gate_text_metadata(text_artist)
                    if gate_text_metadata is None:
                        continue
                    base_font_size = get_base_font_size(
                        text_artist,
                        default=text_artist.get_fontsize(),
                    )
                    text_artist.set_fontsize(
                        _fit_gate_text_font_size_with_context(
                            context=gate_text_context,
                            width=gate_text_metadata.gate_width,
                            height=gate_text_metadata.gate_height,
                            text=text_artist.get_text(),
                            default_font_size=base_font_size,
                            height_fraction=gate_text_metadata.height_fraction,
                            max_font_size=base_font_size * scale_factor,
                            cache={},
                        )
                    )
                state.last_scale_factor = scale_factor
                state.last_points_per_layout_unit = points_per_layout_unit
            finally:
                state.is_updating = False

            if request_redraw and canvas is not None:
                canvas.draw_idle()

        def update_text_scale_on_limits_change(_axes: Axes) -> None:
            apply_text_scale(request_redraw=False)

        if canvas is not None:

            def redraw_text_scale(_event: DrawEvent) -> None:
                apply_text_scale(request_redraw=True)

            state.draw_callback_id = canvas.mpl_connect("draw_event", redraw_text_scale)

        state.xlim_callback_id = axes.callbacks.connect(
            "xlim_changed",
            update_text_scale_on_limits_change,
        )
        state.ylim_callback_id = axes.callbacks.connect(
            "ylim_changed",
            update_text_scale_on_limits_change,
        )
        return

    state.base_view_width = base_view_width
    state.base_view_height = base_view_height
    state.scene = scene
    state.base_points_per_layout_unit = base_gate_text_context.points_per_layout_unit
    state.last_scale_factor = 1.0
    state.last_points_per_layout_unit = base_gate_text_context.points_per_layout_unit


def current_view_size(axes: Axes) -> tuple[float, float]:
    """Return the current visible data window for the axes."""

    x_limits = axes.get_xlim()
    y_limits = axes.get_ylim()
    return abs(x_limits[1] - x_limits[0]), abs(y_limits[1] - y_limits[0])


def current_text_scale(axes: Axes, state: object) -> float:
    """Return the current zoom scale factor for 2D text."""

    from .renderers._matplotlib_figure import TextScalingState

    if not isinstance(state, TextScalingState):
        return 1.0

    current_view_width, current_view_height = current_view_size(axes)
    if current_view_width <= 0.0 or current_view_height <= 0.0:
        return 1.0

    scale_x = state.base_view_width / current_view_width
    scale_y = state.base_view_height / current_view_height
    return max(scale_x, scale_y)


def configure_page_slider(
    *,
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
    set_page_slider: Callable[[Figure, object], None],
) -> None:
    """Attach and wire a slider that scrolls the rendered circuit horizontally."""

    max_scroll = max(0.0, scene.width - viewport_width)
    if max_scroll <= 0.0:
        return

    from matplotlib.widgets import Slider

    slider_axes = figure.add_axes(
        (0.12, 0.045, 0.76, 0.055),
        facecolor=scene.style.theme.axes_facecolor,
    )
    slider = Slider(
        ax=slider_axes,
        label="Scroll",
        valmin=0.0,
        valmax=max_scroll,
        valinit=0.0,
        color=scene.style.theme.gate_edgecolor,
        track_color=scene.style.theme.classical_wire_color,
        handle_style={
            "facecolor": scene.style.theme.accent_color,
            "edgecolor": scene.style.theme.text_color,
            "size": 16,
        },
    )
    slider.label.set_color(scene.style.theme.text_color)
    slider.valtext.set_visible(False)
    slider.track.set_y(0.12)
    slider.track.set_height(0.76)
    slider.track.set_alpha(0.45)
    slider.poly.set_alpha(0.75)
    slider.vline.set_linewidth(3.0)

    set_slider_view(axes, scene, x_offset=0.0, viewport_width=viewport_width)

    def update_scroll(x_offset: float) -> None:
        set_slider_view(axes, scene, x_offset=x_offset, viewport_width=viewport_width)
        if figure.canvas is not None:
            figure.canvas.draw_idle()

    slider.on_changed(update_scroll)
    set_page_slider(figure, slider)


def page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    """Return a readable managed figure size for page-slider mode."""

    width = max(4.8, viewport_width * 0.98)
    height = max(2.0, scene_height * 0.68) + 1.0
    return width, height


def slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    """Estimate the visible scene width for the current axes aspect ratio."""

    axes_width_pixels, axes_height_pixels = axes_viewport_pixels(axes)
    if axes_width_pixels <= 0.0 or axes_height_pixels <= 0.0:
        return scene.width
    viewport_width = scene.height * (axes_width_pixels / axes_height_pixels)
    return min(scene.width, viewport_width)


def set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
) -> None:
    """Set the 2D axes limits used for the slider viewport."""

    axes.set_xlim(x_offset, x_offset + viewport_width)
    axes.set_ylim(scene.height, 0.0)


def is_3d_axes(ax: Axes) -> bool:
    """Return whether the provided axes is a Matplotlib 3D axes."""

    return getattr(ax, "name", "") == "3d"


def is_3d_scene(scene: LayoutScene | LayoutScene3D) -> TypeGuard[LayoutScene3D]:
    """Return whether a prepared scene is a 3D scene."""

    return hasattr(scene, "depth")
