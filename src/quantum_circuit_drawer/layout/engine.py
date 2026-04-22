"""Layout engine that converts IR into a neutral drawing scene."""

from __future__ import annotations

import logging

from ..exceptions import LayoutError
from ..ir.circuit import CircuitIR
from ..style import DrawStyle, normalize_style
from ._layout_scaffold import _LayoutScaffold, build_layout_scaffold
from ._operation_layout import _SceneCollections, build_scene_collections
from .scene import LayoutScene
from .spacing import operation_width_from_parts

logger = logging.getLogger(__name__)


class LayoutEngine:
    """Compute a backend-neutral scene from CircuitIR."""

    def compute(self, circuit: CircuitIR, style: DrawStyle) -> LayoutScene:
        return self._compute_with_normalized_style(
            circuit,
            normalize_style(style),
            hover_enabled=True,
        )

    def _compute_with_normalized_style(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        hover_enabled: bool = True,
    ) -> LayoutScene:
        if not circuit.quantum_wires:
            raise LayoutError("circuit must contain at least one quantum wire")

        scaffold = self._build_layout_scaffold(circuit, style)
        scene_collections = self._build_scene_collections(
            circuit,
            scaffold,
            hover_enabled=hover_enabled,
        )
        scene = LayoutScene(
            width=scaffold.scene_width,
            height=scaffold.scene_height,
            page_height=scaffold.page_height,
            style=scaffold.draw_style,
            wires=scene_collections.wires,
            gates=scene_collections.gates,
            gate_annotations=scene_collections.gate_annotations,
            controls=scene_collections.controls,
            connections=scene_collections.connections,
            swaps=scene_collections.swaps,
            barriers=scene_collections.barriers,
            measurements=scene_collections.measurements,
            texts=scene_collections.texts,
            wire_fold_markers=(),
            pages=scaffold.pages,
            wire_y_positions=scaffold.wire_positions,
            page_count_for_text_scale=len(scaffold.pages),
        )
        logger.debug(
            "Computed layout scene for circuit=%r wires=%d layers=%d pages=%d width=%.2f height=%.2f",
            circuit.name,
            circuit.total_wire_count,
            len(scaffold.normalized_layers),
            len(scaffold.pages),
            scaffold.scene_width,
            scaffold.scene_height,
        )
        return scene

    def _build_layout_scaffold(self, circuit: CircuitIR, style: DrawStyle) -> _LayoutScaffold:
        return build_layout_scaffold(
            circuit,
            style,
            operation_width_resolver=operation_width_from_parts,
        )

    def _build_scene_collections(
        self,
        circuit: CircuitIR,
        scaffold: _LayoutScaffold,
        *,
        hover_enabled: bool = True,
    ) -> _SceneCollections:
        return build_scene_collections(
            circuit,
            scaffold,
            hover_enabled=hover_enabled,
        )
