"""Public API entrypoints."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING

from .exceptions import LayoutError, UnsupportedBackendError
from .style import DrawStyle, normalize_style
from .typing import LayoutEngineLike, OutputPath, RenderResult

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

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
    **options: object,
) -> RenderResult:
    """Draw a quantum circuit from a supported framework."""

    if backend != "matplotlib":
        raise UnsupportedBackendError(f"unsupported backend '{backend}'")

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
    scene = layout_engine.compute(ir, normalized_style)
    renderer = MatplotlibRenderer()
    logger.debug(
        "Prepared render pipeline with adapter=%s, quantum_wires=%d, layers=%d",
        type(adapter).__name__,
        ir.quantum_wire_count,
        len(ir.layers),
    )

    if ax is None:
        figure, axes = _create_managed_figure(scene)
        renderer.render(scene, ax=axes, output=output)
        if show:
            from matplotlib import pyplot as plt

            plt.show()
        return figure, axes

    return renderer.render(scene, ax=ax, output=output)


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


def _create_managed_figure(scene: LayoutScene) -> tuple[Figure, Axes]:
    from matplotlib import pyplot as plt

    figsize = (max(4.0, scene.width * 1.1), max(2.4, scene.height * 0.9))
    figure = plt.figure(figsize=figsize)
    axes = figure.add_subplot(111)
    return figure, axes