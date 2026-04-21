"""Adapter, layout, and renderer preparation for one draw request."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

from ..diagnostics import DiagnosticSeverity, RenderDiagnostic
from ..exceptions import LayoutError, UnsupportedFrameworkError
from ..hover import HoverOptions, normalize_hover
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit, semantic_circuit_from_circuit_ir
from ..ir.semantic import SemanticCircuitIR
from ..style import DrawStyle, normalize_style
from ..topology import (
    HardwareTopology,
    TopologyInput,
    normalize_topology_input,
    topology_display_name,
)
from ..typing import (
    LayoutEngine3DLike,
    LayoutEngineLike,
    _NormalizedLayoutEngine3DLike,
)
from .request import DrawPipelineOptions, ViewMode

if TYPE_CHECKING:
    from ..layout.scene import LayoutScene
    from ..layout.scene_3d import LayoutScene3D
    from ..renderers import BaseRenderer

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedDrawPipeline:
    """Resolved components needed by the final rendering stage."""

    normalized_style: DrawStyle
    ir: CircuitIR
    semantic_ir: SemanticCircuitIR
    layout_engine: LayoutEngineLike | LayoutEngine3DLike
    paged_scene: LayoutScene | LayoutScene3D
    renderer: BaseRenderer
    draw_options: DrawPipelineOptions
    detected_framework: str | None = None
    diagnostics: tuple[RenderDiagnostic, ...] = ()


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

    from ..adapters.registry import get_adapter
    from ..renderers.matplotlib_renderer import MatplotlibRenderer
    from ..renderers.matplotlib_renderer_3d import MatplotlibRenderer3D

    draw_options = coerce_pipeline_options(options)
    adapter_options = draw_options.adapter_options()

    logger.debug(
        "Drawing circuit with backend=%r framework=%r view=%r and %d option(s)",
        "matplotlib",
        framework,
        draw_options.view,
        6 + len(draw_options.extra),
    )

    normalized_style = normalize_style(style)
    pipeline_diagnostics: list[RenderDiagnostic] = []
    resolved_circuit, resolved_framework = _resolve_qasm_input(circuit, framework)
    if isinstance(resolved_circuit, CircuitIR) and resolved_framework in {None, "ir"}:
        ir = resolved_circuit
        semantic_ir = semantic_circuit_from_circuit_ir(ir)
        adapter_name = "IRAdapter(fast-path)"
        detected_framework = "ir"
    else:
        adapter = get_adapter(resolved_circuit, resolved_framework)
        to_semantic_ir = getattr(adapter, "to_semantic_ir", None)
        semantic_ir = (
            to_semantic_ir(resolved_circuit, options=adapter_options)
            if callable(to_semantic_ir)
            else None
        )
        if semantic_ir is None:
            ir = adapter.to_ir(resolved_circuit, options=adapter_options)
            semantic_ir = semantic_circuit_from_circuit_ir(ir)
        else:
            ir = lower_semantic_circuit(semantic_ir)
            pipeline_diagnostics.extend(semantic_ir.diagnostics)
        adapter_name = type(adapter).__name__
        detected_framework = resolved_framework or adapter.framework_name
        raw_diagnostics = ir.metadata.get("diagnostics", ())
        if isinstance(raw_diagnostics, tuple | list):
            pipeline_diagnostics.extend(
                diagnostic
                for diagnostic in raw_diagnostics
                if isinstance(diagnostic, RenderDiagnostic)
            )
    paged_scene: LayoutScene | LayoutScene3D
    layout_engine: LayoutEngineLike | LayoutEngine3DLike
    renderer: BaseRenderer
    if draw_options.view == "3d":
        draw_options, topology_diagnostics = _resolve_topology_menu_options(draw_options)
        pipeline_diagnostics.extend(topology_diagnostics)
        topology = draw_options.topology
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
            topology_display_name(topology),
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
        semantic_ir=semantic_ir,
        layout_engine=layout_engine,
        paged_scene=paged_scene,
        renderer=renderer,
        draw_options=draw_options,
        detected_framework=detected_framework,
        diagnostics=tuple(pipeline_diagnostics),
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
        topology=normalize_topology_input(options.get("topology", "line")),
        topology_menu=bool(options.get("topology_menu", False)),
        direct=bool(options.get("direct", True)),
        hover=_normalize_hover_option(options.get("hover", False)),
        extra={
            key: value
            for key, value in options.items()
            if key not in {"composite_mode", "view", "topology", "topology_menu", "direct", "hover"}
        },
    )


def resolve_layout_engine(layout: LayoutEngineLike | LayoutEngine3DLike | None) -> LayoutEngineLike:
    """Return the default 2D layout engine or validate a custom replacement."""

    from ..layout import LayoutEngine

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

    from ..layout import LayoutEngine3D

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
    from ..layout.engine import LayoutEngine

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
    topology_name: TopologyInput,
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


def _resolve_qasm_input(
    circuit: object,
    framework: str | None,
) -> tuple[object, str | None]:
    if framework == "qasm":
        if not isinstance(circuit, str):
            raise UnsupportedFrameworkError("framework='qasm' requires OpenQASM 2 text input")
        if not _looks_like_openqasm(circuit):
            raise UnsupportedFrameworkError(
                "framework='qasm' requires OpenQASM 2 text starting with 'OPENQASM'"
            )
        return _parse_openqasm_with_qiskit(circuit), "qiskit"
    if isinstance(circuit, str) and framework is None:
        if _looks_like_openqasm(circuit):
            return _parse_openqasm_with_qiskit(circuit), "qiskit"
        raise UnsupportedFrameworkError(
            "string inputs are only supported for OpenQASM 2 text starting with 'OPENQASM'"
        )
    return circuit, framework


def _looks_like_openqasm(value: str) -> bool:
    return value.lstrip().upper().startswith("OPENQASM")


def _parse_openqasm_with_qiskit(qasm_text: str) -> object:
    try:
        import qiskit
    except ModuleNotFoundError as exc:
        raise UnsupportedFrameworkError(
            "OpenQASM input requires the optional dependency 'qiskit'. "
            "Install it with 'pip install quantum-circuit-drawer[qiskit]' or 'pip install qiskit'."
        ) from exc
    return qiskit.QuantumCircuit.from_qasm_str(qasm_text)


def _resolve_topology_menu_options(
    draw_options: DrawPipelineOptions,
) -> tuple[DrawPipelineOptions, tuple[RenderDiagnostic, ...]]:
    topology = draw_options.topology
    if draw_options.topology_menu and isinstance(topology, HardwareTopology):
        return (
            replace(draw_options, topology_menu=False),
            (
                RenderDiagnostic(
                    code="topology_menu_disabled_custom_topology",
                    message=(
                        "Disabled topology_menu because the interactive selector is only "
                        "available for built-in 3D topologies."
                    ),
                    severity=DiagnosticSeverity.INFO,
                ),
            ),
        )
    return draw_options, ()
