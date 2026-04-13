"""Managed-figure rendering helpers for the public drawing API."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, TypeGuard, cast

from ._draw_pipeline import PreparedDrawPipeline
from .renderers._render_support import show_figure_if_supported
from .style import DrawStyle
from .typing import LayoutEngineLike, OutputPath

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D

_PAGE_SLIDER_MAIN_AXES_BOTTOM = 0.18
logger = logging.getLogger(__name__)


def render_managed_draw_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    page_slider: bool,
) -> tuple[Figure, Axes]:
    """Render a prepared pipeline on a managed figure."""

    from .renderers._matplotlib_figure import (
        create_managed_figure,
        set_page_slider,
        set_viewport_width,
    )

    if is_3d_scene(pipeline.paged_scene):
        figure, axes = create_managed_figure(
            pipeline.paged_scene,
            use_agg=not show,
            projection="3d",
        )
        pipeline.renderer.render(pipeline.paged_scene, ax=axes, output=output)
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
        initial_viewport_width = min(scene_2d.width, slider_scene.width)
        figure_width, figure_height = page_slider_figsize(
            initial_viewport_width,
            slider_scene.height,
        )
        if output is None:
            figure, axes = create_managed_figure(
                slider_scene,
                figure_width=figure_width,
                figure_height=figure_height,
                use_agg=not show,
            )
        else:
            figure, axes = create_managed_figure(scene_2d, use_agg=not show)
            pipeline.renderer.render(scene_2d, ax=axes, output=output)
            axes.clear()
            figure.set_size_inches(figure_width, figure_height, forward=True)
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
        figure, axes = create_managed_figure(pipeline.paged_scene, use_agg=not show)
        pipeline.renderer.render(pipeline.paged_scene, ax=axes, output=output)
        logger.debug("Rendered managed figure without page slider")

    show_figure_if_supported(figure, show=show)
    return figure, axes


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

    from matplotlib.figure import Figure

    figure = axes.figure
    assert isinstance(figure, Figure)
    figure_width, figure_height = figure.get_size_inches()
    axes_position = axes.get_position()
    axes_width_pixels = figure_width * figure.dpi * axes_position.width
    axes_height_pixels = figure_height * figure.dpi * axes_position.height
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
