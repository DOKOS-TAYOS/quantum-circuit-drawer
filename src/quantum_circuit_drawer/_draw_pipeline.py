"""Internal draw pipeline preparation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .exceptions import LayoutError
from .style import DrawStyle, normalize_style
from .typing import LayoutEngineLike

if TYPE_CHECKING:
    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .renderers import MatplotlibRenderer

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedDrawPipeline:
    normalized_style: DrawStyle
    ir: CircuitIR
    layout_engine: LayoutEngineLike
    paged_scene: LayoutScene
    renderer: MatplotlibRenderer


def prepare_draw_pipeline(
    *,
    circuit: object,
    framework: str | None,
    style: DrawStyle | Mapping[str, object] | None,
    layout: LayoutEngineLike | None,
    options: Mapping[str, object],
) -> PreparedDrawPipeline:
    """Prepare the adapter, layout scene, and renderer used for drawing."""

    from .adapters.registry import get_adapter
    from .renderers import MatplotlibRenderer

    logger.debug(
        "Drawing circuit with backend=%r framework=%r and %d option(s)",
        "matplotlib",
        framework,
        len(options),
    )

    normalized_style = normalize_style(style)
    adapter = get_adapter(circuit, framework)
    ir = adapter.to_ir(circuit, options=dict(options))
    layout_engine = resolve_layout_engine(layout)
    paged_scene = layout_engine.compute(ir, normalized_style)
    renderer = MatplotlibRenderer()
    logger.debug(
        "Prepared render pipeline with adapter=%s, quantum_wires=%d, layers=%d, pages=%d",
        type(adapter).__name__,
        ir.quantum_wire_count,
        len(ir.layers),
        len(paged_scene.pages),
    )
    return PreparedDrawPipeline(
        normalized_style=normalized_style,
        ir=ir,
        layout_engine=layout_engine,
        paged_scene=paged_scene,
        renderer=renderer,
    )


def resolve_layout_engine(layout: LayoutEngineLike | None) -> LayoutEngineLike:
    """Return the default layout engine or validate a custom one."""

    from .layout import LayoutEngine

    if layout is None:
        return LayoutEngine()
    if isinstance(layout, LayoutEngine):
        return layout
    if hasattr(layout, "compute"):
        return layout
    raise LayoutError("layout must be None or expose a compute(circuit_ir, style) method")
