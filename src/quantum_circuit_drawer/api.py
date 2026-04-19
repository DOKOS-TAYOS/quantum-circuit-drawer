"""Public API orchestration for drawing supported circuit objects.

The functions in this module normalize the user request, validate
high-level runtime constraints, prepare the adapter/layout/renderer
pipeline, and then dispatch to managed or caller-owned Matplotlib
rendering.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Literal

from ._draw_pipeline import prepare_draw_pipeline
from ._draw_request import build_draw_request, validate_draw_request
from .hover import HoverOptions
from .style import DrawStyle
from .typing import LayoutEngine3DLike, LayoutEngineLike, OutputPath, RenderResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from ._draw_pipeline import PreparedDrawPipeline

logger = logging.getLogger(__name__)


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
    figsize: tuple[float, float] | None = None,
    page_slider: bool = False,
    page_window: bool = False,
    composite_mode: str = "compact",
    view: Literal["2d", "3d"] = "2d",
    topology: Literal["line", "grid", "star", "star_tree", "honeycomb"] = "line",
    topology_menu: bool = False,
    direct: bool = True,
    hover: bool | HoverOptions | Mapping[str, object] = False,
    **options: object,
) -> RenderResult:
    """Draw a supported circuit with the current public API contract.

    The function accepts framework objects or the internal ``CircuitIR``,
    normalizes style and rendering options, and then renders through the
    Matplotlib backend.

    Returns:
        ``(figure, axes)`` when ``ax`` is not provided, otherwise the same axes
        object that was passed in.

    Raises:
        UnsupportedBackendError: If ``backend`` is not ``"matplotlib"``.
        UnsupportedFrameworkError: If the circuit cannot be adapted, or an
            explicit ``framework`` does not match the object.
        StyleValidationError: If a style mapping contains unknown or invalid
            values.
        ValueError: If mutually incompatible runtime options are combined, such
            as ``page_slider=True`` with ``ax=...`` or ``view="3d"`` on a 2D
            axes.
        RenderingError: If saving to ``output`` fails.
    """

    request = build_draw_request(
        circuit=circuit,
        framework=framework,
        style=style,
        layout=layout,
        backend=backend,
        ax=ax,
        output=output,
        show=show,
        figsize=figsize,
        page_slider=page_slider,
        page_window=page_window,
        composite_mode=composite_mode,
        view=view,
        topology=topology,
        topology_menu=topology_menu,
        direct=direct,
        hover=hover,
        **options,
    )
    validate_draw_request(request)
    pipeline = prepare_draw_pipeline(
        circuit=request.circuit,
        framework=request.framework,
        style=request.style,
        layout=request.layout,
        options=request.pipeline_options,
    )

    if request.ax is None:
        return _render_managed_draw_pipeline(
            pipeline,
            output=request.output,
            show=request.show,
            figsize=request.figsize,
            page_slider=request.page_slider,
            page_window=request.page_window,
        )

    if request.pipeline_options.view == "3d" and not _is_3d_axes(request.ax):
        raise ValueError("view='3d' requires a 3D Matplotlib axes")
    logger.debug("Rendering scene on caller-managed Matplotlib axes")
    return _render_draw_pipeline_on_axes(
        pipeline,
        axes=request.ax,
        output=request.output,
        enable_auto_paging=request.pipeline_options.view == "2d",
    )


def _render_managed_draw_pipeline(
    pipeline: PreparedDrawPipeline,
    *,
    output: OutputPath | None,
    show: bool,
    figsize: tuple[float, float] | None,
    page_slider: bool,
    page_window: bool,
) -> tuple[Figure, Axes]:
    from ._draw_managed import render_managed_draw_pipeline

    return render_managed_draw_pipeline(
        pipeline,
        output=output,
        show=show,
        figsize=figsize,
        page_slider=page_slider,
        page_window=page_window,
    )


def _render_draw_pipeline_on_axes(
    pipeline: PreparedDrawPipeline,
    *,
    axes: Axes,
    output: OutputPath | None,
    enable_auto_paging: bool,
) -> Axes:
    from ._draw_managed import render_draw_pipeline_on_axes

    return render_draw_pipeline_on_axes(
        pipeline,
        axes=axes,
        output=output,
        enable_auto_paging=enable_auto_paging,
    )


def _is_3d_axes(ax: Axes) -> bool:
    from ._draw_managed import is_3d_axes

    return is_3d_axes(ax)
