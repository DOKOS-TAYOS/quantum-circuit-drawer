"""Public API entrypoints."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING

from .exceptions import LayoutError, UnsupportedBackendError
from .style import DrawStyle, normalize_style
from .typing import LayoutEngineLike, OutputPath, RenderResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene

logger = logging.getLogger(__name__)


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

    if backend != "matplotlib":
        raise UnsupportedBackendError(f"unsupported backend '{backend}'")
    if ax is not None and page_slider:
        raise ValueError(
            "page_slider=True requires a Matplotlib-managed figure and cannot be used with ax"
        )

    logger.debug(
        "Drawing circuit with backend=%r framework=%r and %d option(s)",
        backend,
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
        "Prepared render pipeline with adapter=%s, quantum_wires=%d, layers=%d",
        type(adapter).__name__,
        ir.quantum_wire_count,
        len(ir.layers),
    )

    if ax is None:
        if page_slider:
            slider_scene = _build_continuous_slider_scene(ir, layout_engine, normalized_style)
            viewport_width = min(paged_scene.width, slider_scene.width)
            figure_width, figure_height = _page_slider_figsize(viewport_width, slider_scene.height)
            figure, axes = _create_managed_figure(
                slider_scene,
                figure_width=figure_width,
                figure_height=figure_height,
            )
            if output is not None:
                renderer.render(paged_scene, output=output)
            renderer.render(slider_scene, ax=axes)
            _configure_page_slider(figure, axes, slider_scene, viewport_width)
        else:
            figure, axes = _create_managed_figure(paged_scene)
            renderer.render(paged_scene, ax=axes, output=output)
        if show:
            from matplotlib import pyplot as plt

            plt.show()
        return figure, axes

    return renderer.render(paged_scene, ax=ax, output=output)


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
) -> tuple[Figure, Axes]:
    from matplotlib import pyplot as plt

    figsize = (
        figure_width if figure_width is not None else max(4.0, scene.width * 1.1),
        figure_height if figure_height is not None else max(2.4, scene.height * 0.9),
    )
    figure = plt.figure(figsize=figsize)
    axes = figure.add_subplot(111)
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
) -> None:
    max_scroll = max(0.0, scene.width - viewport_width)
    if max_scroll <= 0.0:
        return

    from matplotlib.widgets import Slider

    figure.subplots_adjust(bottom=0.22)
    slider_axes = figure.add_axes(
        (0.18, 0.08, 0.64, 0.04),
        facecolor=scene.style.theme.axes_facecolor,
    )
    slider = Slider(
        ax=slider_axes,
        label="Scroll",
        valmin=0.0,
        valmax=max_scroll,
        valinit=0.0,
        color=scene.style.theme.gate_edgecolor,
    )
    slider.label.set_color(scene.style.theme.text_color)
    slider.valtext.set_visible(False)

    _set_slider_view(axes, scene, x_offset=0.0, viewport_width=viewport_width)

    def _update_scroll(x_offset: float) -> None:
        _set_slider_view(axes, scene, x_offset=x_offset, viewport_width=viewport_width)
        if figure.canvas is not None:
            figure.canvas.draw_idle()

    slider.on_changed(_update_scroll)
    setattr(figure, "_quantum_circuit_drawer_page_slider", slider)


def _page_slider_figsize(viewport_width: float, scene_height: float) -> tuple[float, float]:
    width = max(4.0, viewport_width * 1.1)
    height = max(2.4, scene_height * 0.9) + 0.8
    return width, height


def _set_slider_view(
    axes: Axes,
    scene: LayoutScene,
    *,
    x_offset: float,
    viewport_width: float,
) -> None:
    axes.set_xlim(x_offset, x_offset + viewport_width)
    axes.set_ylim(scene.height, 0.0)
