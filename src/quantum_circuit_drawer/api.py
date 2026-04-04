"""Public API entrypoints."""

from __future__ import annotations

import logging
from collections.abc import Mapping

from matplotlib.axes import Axes

from .adapters.registry import get_adapter
from .exceptions import LayoutError, UnsupportedBackendError
from .layout import LayoutEngine
from .renderers import MatplotlibRenderer
from .style import DrawStyle, normalize_style
from .typing import LayoutEngineLike, OutputPath, RenderResult

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
    return renderer.render(scene, ax=ax, output=output)


def _resolve_layout_engine(layout: LayoutEngineLike | None) -> LayoutEngineLike:
    if layout is None:
        return LayoutEngine()
    if isinstance(layout, LayoutEngine):
        return layout
    if hasattr(layout, "compute"):
        return layout
    raise LayoutError("layout must be None or expose a compute(circuit_ir, style) method")


def _coerce_options(options: Mapping[str, object]) -> dict[str, object]:
    return dict(options)
