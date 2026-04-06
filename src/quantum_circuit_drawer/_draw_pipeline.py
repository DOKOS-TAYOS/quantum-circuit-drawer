"""Internal draw pipeline preparation."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast

from .exceptions import LayoutError
from .style import DrawStyle, normalize_style
from .typing import LayoutEngine3DLike, LayoutEngineLike

if TYPE_CHECKING:
    from .ir.circuit import CircuitIR
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D
    from .layout.topology_3d import TopologyName
    from .renderers import BaseRenderer

logger = logging.getLogger(__name__)

ViewMode = Literal["2d", "3d"]


@dataclass(frozen=True, slots=True)
class PreparedDrawPipeline:
    normalized_style: DrawStyle
    ir: CircuitIR
    layout_engine: LayoutEngineLike | LayoutEngine3DLike
    paged_scene: LayoutScene | LayoutScene3D
    renderer: BaseRenderer


def prepare_draw_pipeline(
    *,
    circuit: object,
    framework: str | None,
    style: DrawStyle | Mapping[str, object] | None,
    layout: LayoutEngineLike | LayoutEngine3DLike | None,
    options: Mapping[str, object],
) -> PreparedDrawPipeline:
    """Prepare the adapter, layout scene, and renderer used for drawing."""

    from .adapters.registry import get_adapter
    from .renderers import MatplotlibRenderer, MatplotlibRenderer3D

    view = str(options.get("view", "2d")).lower()
    internal_option_keys = {"view", "topology", "direct", "hover"}
    adapter_options = {
        key: value for key, value in options.items() if key not in internal_option_keys
    }

    logger.debug(
        "Drawing circuit with backend=%r framework=%r view=%r and %d option(s)",
        "matplotlib",
        framework,
        view,
        len(options),
    )

    normalized_style = normalize_style(style)
    adapter = get_adapter(circuit, framework)
    ir = adapter.to_ir(circuit, options=adapter_options)
    paged_scene: LayoutScene | LayoutScene3D
    layout_engine: LayoutEngineLike | LayoutEngine3DLike
    renderer: BaseRenderer
    if view == "3d":
        topology = cast("TopologyName", str(options.get("topology", "line")).lower())
        direct = bool(options.get("direct", True))
        hover_enabled = bool(options.get("hover", False))
        layout_engine_3d = resolve_layout_engine_3d(layout)
        paged_scene = layout_engine_3d.compute(
            ir,
            normalized_style,
            topology_name=topology,
            direct=direct,
            hover_enabled=hover_enabled,
        )
        layout_engine = layout_engine_3d
        renderer = MatplotlibRenderer3D()
        logger.debug(
            "Prepared 3D render pipeline with adapter=%s, quantum_wires=%d, layers=%d, topology=%s",
            type(adapter).__name__,
            ir.quantum_wire_count,
            len(ir.layers),
            topology,
        )
    else:
        layout_engine_2d = resolve_layout_engine(layout)
        scene_2d = layout_engine_2d.compute(ir, normalized_style)
        paged_scene = scene_2d
        layout_engine = layout_engine_2d
        renderer = MatplotlibRenderer()
        logger.debug(
            "Prepared render pipeline with adapter=%s, quantum_wires=%d, layers=%d, pages=%d",
            type(adapter).__name__,
            ir.quantum_wire_count,
            len(ir.layers),
            len(scene_2d.pages),
        )
    return PreparedDrawPipeline(
        normalized_style=normalized_style,
        ir=ir,
        layout_engine=layout_engine,
        paged_scene=paged_scene,
        renderer=renderer,
    )


def resolve_layout_engine(layout: LayoutEngineLike | LayoutEngine3DLike | None) -> LayoutEngineLike:
    """Return the default layout engine or validate a custom one."""

    from .layout import LayoutEngine

    if layout is None:
        return LayoutEngine()
    if isinstance(layout, LayoutEngine):
        return layout
    if hasattr(layout, "compute"):
        return cast(LayoutEngineLike, layout)
    raise LayoutError("layout must be None or expose a compute(circuit_ir, style) method")


def resolve_layout_engine_3d(
    layout: LayoutEngineLike | LayoutEngine3DLike | None,
) -> LayoutEngine3DLike:
    """Return the default 3D layout engine or validate a custom one."""

    from .layout import LayoutEngine3D

    if layout is None:
        return LayoutEngine3D()
    if isinstance(layout, LayoutEngine3D):
        return layout
    if hasattr(layout, "compute"):
        return cast(LayoutEngine3DLike, layout)
    raise LayoutError("layout must be None or expose a compute(circuit_ir, style) method")
