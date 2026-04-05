"""Public API entrypoints."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .exceptions import LayoutError, UnsupportedBackendError
from .style import DrawStyle, normalize_style
from .typing import LayoutEngineLike, OutputPath, RenderResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .adapters.base import BaseAdapter
    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .renderers import MatplotlibRenderer

logger = logging.getLogger(__name__)

_NON_INTERACTIVE_BACKENDS = frozenset({"agg", "cairo", "pdf", "pgf", "ps", "svg", "template"})
_MANAGED_SUBPLOT_LEFT = 0.02
_MANAGED_SUBPLOT_RIGHT = 0.98
_MANAGED_SUBPLOT_TOP = 0.98
_MANAGED_SUBPLOT_BOTTOM = 0.02
_PAGE_SLIDER_MAIN_AXES_BOTTOM = 0.18


@dataclass(frozen=True, slots=True)
class _PreparedDrawPipeline:
    normalized_style: DrawStyle
    adapter: BaseAdapter
    ir: CircuitIR
    layout_engine: LayoutEngineLike
    paged_scene: LayoutScene
    renderer: MatplotlibRenderer


def draw_quantum_circuit(
    circuit: object,
    framework: str | None = None,
    *,
    style: DrawStyle | Mapping[str, object] | None = None,
    layout: LayoutEngineLike | None = None,
    backend: str = "matplotlib",
    ax: Axes | None = None,
    output: OutputPath | None = None,
    show: bool = True,
    page_slider: bool = False,
    **options: object,
) -> RenderResult:
    """Draw a quantum circuit from a supported framework."""

    _validate_draw_request(backend=backend, ax=ax, page_slider=page_slider)
    pipeline = _prepare_draw_pipeline(
        circuit=circuit,
        framework=framework,
        style=style,
        layout=layout,
        options=options,
    )

    if ax is None:
        return _render_managed_figure(
            pipeline,
            output=output,
            show=show,
            page_slider=page_slider,
        )

    logger.debug("Rendering scene on caller-managed Matplotlib axes")
    return pipeline.renderer.render(pipeline.paged_scene, ax=ax, output=output)


def _validate_draw_request(
    *,
    backend: str,
    ax: Axes | None,
    page_slider: bool,
) -> None:
    if backend != "matplotlib":
        raise UnsupportedBackendError(f"unsupported backend '{backend}'")
    if ax is not None and page_slider:
        raise ValueError(
            "page_slider=True requires a Matplotlib-managed figure and cannot be used with ax"
        )


def _prepare_draw_pipeline(
    *,
    circuit: object,
    framework: str | None,
    style: DrawStyle | Mapping[str, object] | None,
    layout: LayoutEngineLike | None,
    options: Mapping[str, object],
) -> _PreparedDrawPipeline:
    logger.debug(
        "Drawing circuit with backend=%r framework=%r and %d option(s)",
        "matplotlib",
        framework,
        len(options),
    )

    from .adapters.registry import get_adapter
    from .renderers import MatplotlibRenderer

    normalized_style = normalize_style(style)
    adapter = get_adapter(circuit, framework)
    ir = adapter.to_ir(circuit, options=_coerce_options(options))
    layout_engine = _resolve_layout_engine(layout)
    paged_scene = layout_engine.compute(ir, normalized_style)
    renderer = MatplotlibRenderer()
    logger.debug(
        "Prepared render pipeline with adapter=%s, quantum_wires=%d, layers=%d, pages=%d",
        type(adapter).__name__,
        ir.quantum_wire_count,
        len(ir.layers),
        len(paged_scene.pages),
    )
    return _PreparedDrawPipeline(
        normalized_style=normalized_style,
        adapter=adapter,
        ir=ir,
        layout_engine=layout_engine,
        paged_scene=paged_scene,
        renderer=renderer,
    )


def _render_managed_figure(
    pipeline: _PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    page_slider: bool,
) -> tuple[Figure, Axes]:
    if page_slider:
        slider_scene = _build_continuous_slider_scene(
            pipeline.ir,
            pipeline.layout_engine,
            pipeline.normalized_style,
        )
        initial_viewport_width = min(pipeline.paged_scene.width, slider_scene.width)
        figure_width, figure_height = _page_slider_figsize(
            initial_viewport_width,
            slider_scene.height,
        )
        figure, axes = _create_managed_figure(
            slider_scene,
            figure_width=figure_width,
            figure_height=figure_height,
            use_agg=not show,
        )
        figure.subplots_adjust(bottom=_PAGE_SLIDER_MAIN_AXES_BOTTOM)
        viewport_width = _slider_viewport_width(axes, slider_scene)
        setattr(figure, "_quantum_circuit_drawer_viewport_width", viewport_width)
        if output is not None:
            pipeline.renderer.render(pipeline.paged_scene, output=output)
        pipeline.renderer.render(slider_scene, ax=axes)
        _configure_page_slider(figure, axes, slider_scene, viewport_width)
        logger.debug(
            "Rendered managed figure with page slider viewport_width=%.2f pages=%d",
            viewport_width,
            len(pipeline.paged_scene.pages),
        )
    else:
        figure, axes = _create_managed_figure(pipeline.paged_scene, use_agg=not show)
        pipeline.renderer.render(pipeline.paged_scene, ax=axes, output=output)
        logger.debug("Rendered managed figure without page slider")

    _show_managed_figure_if_supported(figure, show=show)
    return figure, axes


def _resolve_layout_engine(layout: LayoutEngineLike | None) -> LayoutEngineLike:
    from .layout import LayoutEngine

    if layout is None:
        return LayoutEngine()
    if isinstance(layout, LayoutEngine):
        return layout
    if hasattr(layout, "compute"):
        return layout
    raise LayoutError("layout must be None or expose a compute(circuit_ir, style) method")


def _coerce_options(options: Mapping[str, object]) -> dict[str, object]:
    return dict(options)


def _create_managed_figure(
    scene: LayoutScene,
    *,
    figure_width: float | None = None,
    figure_height: float | None = None,
    use_agg: bool = False,
) -> tuple[Figure, Axes]:
    if use_agg:
        return _create_agg_managed_figure(
            scene,
            figure_width=figure_width,
            figure_height=figure_height,
        )

    from matplotlib import pyplot as plt

    figsize = (
        figure_width if figure_width is not None else max(4.6, scene.width * 0.95),
        figure_height if figure_height is not None else max(2.1, scene.height * 0.72),
    )
    figure = plt.figure(figsize=figsize)
    axes = figure.add_subplot(111)
    _configure_managed_axes_padding(figure)
    return figure, axes


def _create_agg_managed_figure(
    scene: LayoutScene,
    *,
    figure_width: float | None = None,
    figure_height: float | None = None,
) -> tuple[Figure, Axes]:
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figsize = (
        figure_width if figure_width is not None else max(4.6, scene.width * 0.95),
        figure_height if figure_height is not None else max(2.1, scene.height * 0.72),
    )
    figure = Figure(figsize=figsize)
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    _configure_managed_axes_padding(figure)
    return figure, axes


def _build_continuous_slider_scene(
    circuit: CircuitIR,
    layout_engine: LayoutEngineLike,
    style: DrawStyle,
) -> LayoutScene:
    return layout_engine.compute(circuit, replace(style, max_page_width=float("inf")))


def _configure_managed_axes_padding(figure: Figure) -> None:
    figure.subplots_adjust(
        left=_MANAGED_SUBPLOT_LEFT,
        right=_MANAGED_SUBPLOT_RIGHT,
        top=_MANAGED_SUBPLOT_TOP,
        bottom=_MANAGED_SUBPLOT_BOTTOM,
    )


def _configure_page_slider(
    figure: Figure,
    axes: Axes,
    scene: LayoutScene,
    viewport_width: float,
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
    setattr(figure, "_quantum_circuit_drawer_page_slider", slider)


def _page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    width = max(4.8, viewport_width * 0.98)
    height = max(2.0, scene_height * 0.68) + 1.0
    return width, height


def _slider_viewport_width(axes: Axes, scene: LayoutScene) -> float:
    figure = axes.figure
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


def _figure_backend_name(figure: Figure) -> str:
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
