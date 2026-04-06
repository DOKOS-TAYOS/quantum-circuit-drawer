"""Public API entrypoints."""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Literal, TypeGuard, cast

from ._draw_pipeline import PreparedDrawPipeline, prepare_draw_pipeline
from .exceptions import UnsupportedBackendError
from .style import DrawStyle
from .typing import LayoutEngine3DLike, LayoutEngineLike, OutputPath, RenderResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure, SubFigure

    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D

logger = logging.getLogger(__name__)

_NON_INTERACTIVE_BACKENDS = frozenset({"agg", "cairo", "pdf", "pgf", "ps", "svg", "template"})
_PAGE_SLIDER_MAIN_AXES_BOTTOM = 0.18


def draw_quantum_circuit(
    circuit: object,
    framework: str | None = None,
    *,
    style: DrawStyle | Mapping[str, object] | None = None,
    layout: LayoutEngineLike | LayoutEngine3DLike | None = None,
    backend: str = "matplotlib",
    ax: Axes | None = None,
    output: OutputPath | None = None,
    show: bool = True,
    page_slider: bool = False,
    composite_mode: str = "compact",
    view: Literal["2d", "3d"] = "2d",
    topology: Literal["line", "grid", "star", "star_tree", "honeycomb"] = "line",
    direct: bool = True,
    hover: bool = False,
    **options: object,
) -> RenderResult:
    """Draw a quantum circuit from a supported framework."""

    _validate_draw_request(backend=backend, ax=ax, page_slider=page_slider, view=view)
    effective_hover = _resolve_effective_hover(
        hover=hover,
        view=view,
        ax=ax,
        output=output,
        show=show,
    )
    pipeline = prepare_draw_pipeline(
        circuit=circuit,
        framework=framework,
        style=style,
        layout=layout,
        options={
            "composite_mode": composite_mode,
            "view": view,
            "topology": topology,
            "direct": direct,
            "hover": effective_hover,
            **options,
        },
    )

    if ax is None:
        return _render_managed_figure(
            pipeline,
            output=output,
            show=show,
            page_slider=page_slider,
        )

    if view == "3d" and not _is_3d_axes(ax):
        raise ValueError("view='3d' requires a 3D Matplotlib axes")
    logger.debug("Rendering scene on caller-managed Matplotlib axes")
    return pipeline.renderer.render(pipeline.paged_scene, ax=ax, output=output)


def _validate_draw_request(
    *,
    backend: str,
    ax: Axes | None,
    page_slider: bool,
    view: Literal["2d", "3d"],
) -> None:
    if backend != "matplotlib":
        raise UnsupportedBackendError(f"unsupported backend '{backend}'")
    if ax is not None and page_slider:
        raise ValueError(
            "page_slider=True requires a Matplotlib-managed figure and cannot be used with ax"
        )
    if view == "3d" and page_slider:
        raise ValueError("page_slider=True is only supported for view='2d'")


def _render_managed_figure(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    page_slider: bool,
) -> tuple[Figure, Axes]:
    from .renderers._matplotlib_figure import (
        create_managed_figure,
        set_page_slider,
        set_viewport_width,
    )

    if _is_3d_scene(pipeline.paged_scene):
        figure, axes = create_managed_figure(
            pipeline.paged_scene,
            use_agg=not show,
            projection="3d",
        )
        pipeline.renderer.render(pipeline.paged_scene, ax=axes, output=output)
        logger.debug("Rendered managed 3D figure without page slider")
        _show_managed_figure_if_supported(figure, show=show)
        return figure, axes

    if page_slider:
        scene_2d = cast("LayoutScene", pipeline.paged_scene)
        layout_engine = cast(LayoutEngineLike, pipeline.layout_engine)
        slider_scene = _build_continuous_slider_scene(
            pipeline.ir,
            layout_engine,
            pipeline.normalized_style,
        )
        initial_viewport_width = min(scene_2d.width, slider_scene.width)
        figure_width, figure_height = _page_slider_figsize(
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
        viewport_width = _slider_viewport_width(axes, slider_scene)
        set_viewport_width(figure, viewport_width=viewport_width)
        pipeline.renderer.render(slider_scene, ax=axes)
        _configure_page_slider(
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

    _show_managed_figure_if_supported(figure, show=show)
    return figure, axes


def _build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
) -> LayoutScene:
    return layout_engine.compute(circuit, replace(style, max_page_width=float("inf")))


def _configure_page_slider(
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
    set_page_slider: Callable[[Figure, object], None],
) -> None:
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

    _set_slider_view(axes, scene, x_offset=0.0, viewport_width=viewport_width)

    def _update_scroll(x_offset: float) -> None:
        _set_slider_view(axes, scene, x_offset=x_offset, viewport_width=viewport_width)
        if figure.canvas is not None:
            figure.canvas.draw_idle()

    slider.on_changed(_update_scroll)
    set_page_slider(figure, slider)


def _page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    width = max(4.8, viewport_width * 0.98)
    height = max(2.0, scene_height * 0.68) + 1.0
    return width, height


def _slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    figure = axes.figure
    from matplotlib.figure import Figure

    assert isinstance(figure, Figure)
    figure_width, figure_height = figure.get_size_inches()
    axes_position = axes.get_position()
    axes_width_pixels = figure_width * figure.dpi * axes_position.width
    axes_height_pixels = figure_height * figure.dpi * axes_position.height
    if axes_width_pixels <= 0.0 or axes_height_pixels <= 0.0:
        return scene.width
    viewport_width = scene.height * (axes_width_pixels / axes_height_pixels)
    return min(scene.width, viewport_width)


def _set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
) -> None:
    axes.set_xlim(x_offset, x_offset + viewport_width)
    axes.set_ylim(scene.height, 0.0)


def _show_managed_figure_if_supported(figure: Figure, *, show: bool) -> None:
    if not show:
        logger.debug("Skipping pyplot.show() because show=False")
        return

    from matplotlib import pyplot as plt

    show_function = plt.show
    backend_name = _figure_backend_name(figure)
    if backend_name in _NON_INTERACTIVE_BACKENDS and _is_builtin_pyplot_show(show_function):
        logger.debug(
            "Skipping pyplot.show() for non-interactive backend=%r",
            backend_name,
        )
        return

    show_function()


def _is_builtin_pyplot_show(show_function: object) -> bool:
    return getattr(show_function, "__module__", "") == "matplotlib.pyplot"


def _figure_backend_name(figure: Figure | SubFigure) -> str:
    canvas_name = type(figure.canvas).__name__.lower()
    if canvas_name.startswith("figurecanvas"):
        return _normalize_backend_name(canvas_name.removeprefix("figurecanvas"))

    from matplotlib import pyplot as plt

    return _normalize_backend_name(str(plt.get_backend()))


def _normalize_backend_name(backend_name: str) -> str:
    normalized_name = backend_name.strip().lower()
    for prefix in (
        "module://matplotlib.backends.backend_",
        "matplotlib.backends.backend_",
        "backend_",
    ):
        if normalized_name.startswith(prefix):
            normalized_name = normalized_name.removeprefix(prefix)
    return normalized_name


def _is_3d_axes(ax: Axes) -> bool:
    return getattr(ax, "name", "") == "3d"


def _is_3d_scene(scene: LayoutScene | LayoutScene3D) -> TypeGuard[LayoutScene3D]:
    return hasattr(scene, "depth")


def _resolve_effective_hover(
    *,
    hover: bool,
    view: Literal["2d", "3d"],
    ax: Axes | None,
    output: OutputPath | None,
    show: bool,
) -> bool:
    if not hover or view != "3d" or output is not None:
        return False
    if ax is not None:
        return _figure_backend_name(ax.figure) not in _NON_INTERACTIVE_BACKENDS
    if not show:
        return False
    from matplotlib import pyplot as plt

    return _normalize_backend_name(str(plt.get_backend())) not in _NON_INTERACTIVE_BACKENDS
