"""Adapter, layout, and renderer preparation for one draw request."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from ._draw_request import DrawPipelineOptions, TopologyMode, ViewMode
from .exceptions import LayoutError
from .hover import HoverOptions, normalize_hover
from .ir.circuit import CircuitIR
from .style import DrawStyle, normalize_style
from .typing import (
    LayoutEngine3DLike,
    LayoutEngineLike,
    _NormalizedLayoutEngine3DLike,
)

if TYPE_CHECKING:
    from .layout.scene import LayoutScene
    from .layout.scene_3d import LayoutScene3D
    from .layout.topology_3d import TopologyName
    from .renderers import BaseRenderer

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedDrawPipeline:
    """Resolved components needed by the final rendering stage."""

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
    options: Mapping[str, object] | DrawPipelineOptions,
) -> PreparedDrawPipeline:
    """Prepare the adapter, layout scene, and renderer used for drawing.

    The resulting object is the handoff point between public request
    validation and actual Matplotlib rendering.
    """

    from .adapters.registry import get_adapter
    from .renderers.matplotlib_renderer import MatplotlibRenderer
    from .renderers.matplotlib_renderer_3d import MatplotlibRenderer3D

    draw_options = coerce_pipeline_options(options)
    adapter_options = draw_options.adapter_options()

    logger.debug(
        "Drawing circuit with backend=%r framework=%r view=%r and %d option(s)",
        "matplotlib",
        framework,
        draw_options.view,
        len(draw_options.to_mapping()),
    )

    normalized_style = normalize_style(style)
    adapter_name = "unknown"
    if isinstance(circuit, CircuitIR) and framework in {None, "ir"}:
        ir = circuit
        adapter_name = "IRAdapter(fast-path)"
    else:
        adapter = get_adapter(circuit, framework)
        ir = adapter.to_ir(circuit, options=adapter_options)
        adapter_name = type(adapter).__name__
    paged_scene: LayoutScene | LayoutScene3D
    layout_engine: LayoutEngineLike | LayoutEngine3DLike
    renderer: BaseRenderer
    if draw_options.view == "3d":
        topology: TopologyName = draw_options.topology
        direct = draw_options.direct
        hover_enabled = draw_options.hover.enabled
        layout_engine_3d = resolve_layout_engine_3d(layout)
        paged_scene = _compute_3d_scene(
            layout_engine_3d,
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
            adapter_name,
            ir.quantum_wire_count,
            len(ir.layers),
            topology,
        )
    else:
        layout_engine_2d = resolve_layout_engine(layout)
        scene_2d = _compute_2d_scene(
            layout_engine_2d,
            ir,
            normalized_style,
            hover_enabled=draw_options.hover.enabled,
        )
        scene_2d.hover = draw_options.hover
        paged_scene = scene_2d
        layout_engine = layout_engine_2d
        renderer = MatplotlibRenderer()
        logger.debug(
            "Prepared render pipeline with adapter=%s, quantum_wires=%d, layers=%d, pages=%d",
            adapter_name,
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


def coerce_pipeline_options(
    options: Mapping[str, object] | DrawPipelineOptions,
) -> DrawPipelineOptions:
    """Normalize legacy mapping options into ``DrawPipelineOptions``."""

    if isinstance(options, DrawPipelineOptions):
        return options
    return DrawPipelineOptions(
        composite_mode=str(options.get("composite_mode", "compact")),
        view=cast(ViewMode, str(options.get("view", "2d"))),
        topology=cast(TopologyMode, str(options.get("topology", "line"))),
        direct=bool(options.get("direct", True)),
        hover=_normalize_hover_option(options.get("hover", False)),
        extra={
            key: value
            for key, value in options.items()
            if key not in {"composite_mode", "view", "topology", "direct", "hover"}
        },
    )


def resolve_layout_engine(layout: LayoutEngineLike | LayoutEngine3DLike | None) -> LayoutEngineLike:
    """Return the default 2D layout engine or validate a custom replacement."""

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
    """Return the default 3D layout engine or validate a custom replacement."""

    from .layout import LayoutEngine3D

    if layout is None:
        return LayoutEngine3D()
    if isinstance(layout, LayoutEngine3D):
        return layout
    if hasattr(layout, "compute"):
        return cast(LayoutEngine3DLike, layout)
    raise LayoutError("layout must be None or expose a compute(circuit_ir, style) method")


def _compute_2d_scene(
    layout_engine: LayoutEngineLike,
    circuit: CircuitIR,
    style: DrawStyle,
    *,
    hover_enabled: bool,
) -> LayoutScene:
    from .layout.engine import LayoutEngine

    if isinstance(layout_engine, LayoutEngine):
        return layout_engine._compute_with_normalized_style(
            circuit,
            style,
            hover_enabled=hover_enabled,
        )
    return layout_engine.compute(circuit, style)


def _compute_3d_scene(
    layout_engine: LayoutEngine3DLike,
    circuit: CircuitIR,
    style: DrawStyle,
    *,
    topology_name: TopologyName,
    direct: bool,
    hover_enabled: bool,
) -> LayoutScene3D:
    if hasattr(layout_engine, "_compute_with_normalized_style"):
        return cast(_NormalizedLayoutEngine3DLike, layout_engine)._compute_with_normalized_style(
            circuit,
            style,
            topology_name=topology_name,
            direct=direct,
            hover_enabled=hover_enabled,
        )
    return layout_engine.compute(
        circuit,
        style,
        topology_name=topology_name,
        direct=direct,
        hover_enabled=hover_enabled,
    )


def _normalize_hover_option(value: object) -> HoverOptions:
    return normalize_hover(cast("bool | HoverOptions | Mapping[str, object]", value))
