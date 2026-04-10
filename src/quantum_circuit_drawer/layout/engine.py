"""Layout engine that converts IR into a neutral drawing scene."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, replace

from ..exceptions import LayoutError
from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from ..ir.wires import WireIR
from ..style import DrawStyle, normalize_style
from ._classical_conditions import iter_classical_condition_anchors
from ._layering import normalize_draw_layers
from ._operation_text import build_operation_text_metrics
from .routing import vertical_span
from .scene import (
    GateRenderStyle,
    LayoutScene,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    ScenePage,
    SceneSwap,
    SceneText,
    SceneWire,
)
from .spacing import estimate_text_width, operation_width_from_parts

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _OperationMetrics:
    width: float
    label: str
    display_label: str
    subtitle: str | None


@dataclass(frozen=True, slots=True)
class _LayoutScaffold:
    draw_style: DrawStyle
    normalized_layers: tuple[LayerIR, ...]
    operation_metrics: dict[int, _OperationMetrics]
    wire_positions: dict[str, float]
    column_widths: tuple[float, ...]
    x_centers: tuple[float, ...]
    pages: tuple[ScenePage, ...]
    page_height: float
    scene_width: float
    scene_height: float


@dataclass(frozen=True, slots=True)
class _SceneCollections:
    wires: tuple[SceneWire, ...]
    texts: tuple[SceneText, ...]
    gates: tuple[SceneGate, ...]
    gate_annotations: tuple[SceneGateAnnotation, ...]
    controls: tuple[SceneControl, ...]
    connections: tuple[SceneConnection, ...]
    swaps: tuple[SceneSwap, ...]
    barriers: tuple[SceneBarrier, ...]
    measurements: tuple[SceneMeasurement, ...]


class LayoutEngine:
    """Compute a backend-neutral scene from CircuitIR."""

    def compute(self, circuit: CircuitIR, style: DrawStyle) -> LayoutScene:
        if not circuit.quantum_wires:
            raise LayoutError("circuit must contain at least one quantum wire")

        scaffold = self._build_layout_scaffold(circuit, style)
        scene_collections = self._build_scene_collections(circuit, scaffold)
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
            pages=scaffold.pages,
            wire_y_positions=scaffold.wire_positions,
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
        draw_style = self._resolve_scene_style(circuit, normalize_style(style))
        normalized_layers = normalize_draw_layers(circuit)
        operation_metrics = self._build_operation_metrics(normalized_layers, draw_style)
        wire_positions = self._build_wire_positions(circuit, draw_style)
        column_widths = tuple(
            self._build_column_widths(normalized_layers, operation_metrics, draw_style)
        )
        x_centers = tuple(self._build_column_centers(column_widths, draw_style))
        page_height = max(wire_positions.values()) + draw_style.margin_bottom
        pages = self._build_pages(column_widths, x_centers, page_height, draw_style)
        scene_width = max(
            (
                draw_style.margin_left + page.content_width + draw_style.margin_right
                for page in pages
            ),
            default=self._scene_width(column_widths, draw_style),
        )
        scene_height = page_height + (
            (len(pages) - 1) * (page_height + draw_style.page_vertical_gap)
        )
        return _LayoutScaffold(
            draw_style=draw_style,
            normalized_layers=normalized_layers,
            operation_metrics=operation_metrics,
            wire_positions=wire_positions,
            column_widths=column_widths,
            x_centers=x_centers,
            pages=pages,
            page_height=page_height,
            scene_width=scene_width,
            scene_height=scene_height,
        )

    def _resolve_scene_style(self, circuit: CircuitIR, style: DrawStyle) -> DrawStyle:
        left_margin = style.margin_left
        if style.show_wire_labels:
            widest_label = max(
                (
                    estimate_text_width(wire.label or wire.id, style.font_size * 0.82)
                    for wire in circuit.all_wires
                ),
                default=0.0,
            )
            left_margin = max(left_margin, widest_label + style.label_margin + 0.12)
        return replace(style, margin_left=left_margin, margin_right=max(0.22, style.margin_right))

    def _build_scene_collections(
        self,
        circuit: CircuitIR,
        scaffold: _LayoutScaffold,
    ) -> _SceneCollections:
        wire_map = circuit.wire_map
        wires = tuple(
            SceneWire(
                id=wire.id,
                label=wire.label or wire.id,
                kind=wire.kind,
                y=scaffold.wire_positions[wire.id],
                x_start=scaffold.draw_style.margin_left,
                x_end=scaffold.draw_style.margin_left
                + (
                    scaffold.pages[0].content_width
                    if scaffold.pages
                    else scaffold.draw_style.gate_width
                ),
                bundle_size=self._bundle_size(wire),
            )
            for wire in circuit.all_wires
        )
        texts = self._wire_labels(circuit, scaffold.wire_positions, scaffold.draw_style)
        gates: list[SceneGate] = []
        gate_annotations: list[SceneGateAnnotation] = []
        controls: list[SceneControl] = []
        connections: list[SceneConnection] = []
        swaps: list[SceneSwap] = []
        barriers: list[SceneBarrier] = []
        measurements: list[SceneMeasurement] = []

        for column, layer in enumerate(scaffold.normalized_layers):
            x = scaffold.x_centers[column]
            for operation in layer.operations:
                self._layout_operation(
                    operation=operation,
                    metrics=scaffold.operation_metrics[id(operation)],
                    column=column,
                    x=x,
                    style=scaffold.draw_style,
                    wire_map=wire_map,
                    wire_positions=scaffold.wire_positions,
                    gates=gates,
                    gate_annotations=gate_annotations,
                    controls=controls,
                    connections=connections,
                    swaps=swaps,
                    barriers=barriers,
                    measurements=measurements,
                )

        return _SceneCollections(
            wires=wires,
            texts=texts,
            gates=tuple(gates),
            gate_annotations=tuple(gate_annotations),
            controls=tuple(controls),
            connections=tuple(connections),
            swaps=tuple(swaps),
            barriers=tuple(barriers),
            measurements=tuple(measurements),
        )

    def _build_operation_metrics(
        self, layers: Sequence[LayerIR], style: DrawStyle
    ) -> dict[int, _OperationMetrics]:
        text_metrics = build_operation_text_metrics(layers, style)
        metrics: dict[int, _OperationMetrics] = {}
        cached_widths: dict[tuple[OperationKind, str, str | None], float] = {}
        for layer in layers:
            for operation in layer.operations:
                operation_text = text_metrics[id(operation)]
                width_key = (
                    operation.kind,
                    operation_text.label,
                    operation_text.subtitle,
                )
                width = cached_widths.get(width_key)
                if width is None:
                    width = operation_width_from_parts(
                        operation=operation,
                        style=style,
                        label=operation_text.label,
                        subtitle=operation_text.subtitle,
                    )
                    cached_widths[width_key] = width
                metrics[id(operation)] = _OperationMetrics(
                    width=width,
                    label=operation_text.label,
                    display_label=operation_text.display_label,
                    subtitle=operation_text.subtitle,
                )
        return metrics

    def _build_wire_positions(self, circuit: CircuitIR, style: DrawStyle) -> dict[str, float]:
        positions: dict[str, float] = {}
        current_y = style.margin_top
        for wire in circuit.quantum_wires:
            positions[wire.id] = current_y
            current_y += style.wire_spacing
        if circuit.classical_wires:
            current_y += style.classical_wire_gap
            for wire in circuit.classical_wires:
                positions[wire.id] = current_y
                current_y += style.wire_spacing
        return positions

    def _bundle_size(self, wire: WireIR) -> int:
        bundle_size = wire.metadata.get("bundle_size", 1)
        return int(bundle_size) if isinstance(bundle_size, int | float | str) else 1

    def _build_column_widths(
        self,
        layers: Sequence[LayerIR],
        operation_metrics: dict[int, _OperationMetrics],
        style: DrawStyle,
    ) -> list[float]:
        widths: list[float] = []
        for layer in layers:
            if not layer.operations:
                widths.append(style.gate_width)
                continue
            widths.append(
                max(operation_metrics[id(operation)].width for operation in layer.operations)
            )
        return widths

    def _build_column_centers(self, widths: Sequence[float], style: DrawStyle) -> list[float]:
        centers: list[float] = []
        current_x = style.margin_left
        for width in widths:
            centers.append(current_x + width / 2)
            current_x += width + style.layer_spacing
        return centers

    def _scene_width(self, widths: Sequence[float], style: DrawStyle) -> float:
        if not widths:
            return style.margin_left + style.margin_right + style.gate_width
        total_columns = sum(widths)
        total_spacing = style.layer_spacing * max(0, len(widths) - 1)
        return style.margin_left + total_columns + total_spacing + style.margin_right

    def _build_pages(
        self,
        widths: Sequence[float],
        x_centers: Sequence[float],
        page_height: float,
        style: DrawStyle,
    ) -> tuple[ScenePage, ...]:
        if not widths:
            return (
                ScenePage(
                    index=0,
                    start_column=0,
                    end_column=0,
                    content_x_start=style.margin_left,
                    content_x_end=style.margin_left + style.gate_width,
                    content_width=style.gate_width,
                    y_offset=0.0,
                ),
            )

        pages: list[ScenePage] = []
        start_column = 0
        current_width = 0.0
        for column, width in enumerate(widths):
            proposed_width = (
                width if current_width == 0.0 else current_width + style.layer_spacing + width
            )
            if current_width > 0.0 and proposed_width > style.max_page_width:
                pages.append(
                    self._make_page(
                        index=len(pages),
                        start_column=start_column,
                        end_column=column - 1,
                        widths=widths,
                        x_centers=x_centers,
                        page_height=page_height,
                        style=style,
                    )
                )
                start_column = column
                current_width = width
            else:
                current_width = proposed_width

        pages.append(
            self._make_page(
                index=len(pages),
                start_column=start_column,
                end_column=len(widths) - 1,
                widths=widths,
                x_centers=x_centers,
                page_height=page_height,
                style=style,
            )
        )
        return tuple(pages)

    def _make_page(
        self,
        *,
        index: int,
        start_column: int,
        end_column: int,
        widths: Sequence[float],
        x_centers: Sequence[float],
        page_height: float,
        style: DrawStyle,
    ) -> ScenePage:
        content_x_start = x_centers[start_column] - (widths[start_column] / 2)
        content_x_end = x_centers[end_column] + (widths[end_column] / 2)
        return ScenePage(
            index=index,
            start_column=start_column,
            end_column=end_column,
            content_x_start=content_x_start,
            content_x_end=content_x_end,
            content_width=content_x_end - content_x_start,
            y_offset=index * (page_height + style.page_vertical_gap),
        )

    def _wire_labels(
        self, circuit: CircuitIR, wire_positions: dict[str, float], style: DrawStyle
    ) -> tuple[SceneText, ...]:
        if not style.show_wire_labels:
            return ()
        labels = [
            SceneText(
                x=style.margin_left - style.label_margin,
                y=wire_positions[wire.id],
                text=wire.label or wire.id,
                ha="right",
                font_size=style.font_size,
            )
            for wire in circuit.all_wires
        ]
        return tuple(labels)

    def _layout_operation(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
        style: DrawStyle,
        wire_map: dict[str, WireIR],
        wire_positions: dict[str, float],
        gates: list[SceneGate],
        gate_annotations: list[SceneGateAnnotation],
        controls: list[SceneControl],
        connections: list[SceneConnection],
        swaps: list[SceneSwap],
        barriers: list[SceneBarrier],
        measurements: list[SceneMeasurement],
    ) -> None:
        if isinstance(operation, MeasurementIR) or operation.kind is OperationKind.MEASUREMENT:
            self._layout_measurement(
                operation=operation,
                metrics=metrics,
                column=column,
                x=x,
                style=style,
                wire_map=wire_map,
                wire_positions=wire_positions,
                connections=connections,
                measurements=measurements,
            )
            return

        if operation.kind is OperationKind.BARRIER:
            self._layout_barrier(
                operation=operation,
                column=column,
                x=x,
                wire_positions=wire_positions,
                barriers=barriers,
            )
            return

        if operation.kind is OperationKind.SWAP:
            self._layout_swap(
                operation=operation,
                column=column,
                x=x,
                style=style,
                wire_positions=wire_positions,
                connections=connections,
                swaps=swaps,
            )
            return

        if operation.kind is OperationKind.CONTROLLED_GATE:
            self._layout_controlled_gate(
                operation=operation,
                metrics=metrics,
                column=column,
                x=x,
                style=style,
                wire_positions=wire_positions,
                gates=gates,
                gate_annotations=gate_annotations,
                controls=controls,
                connections=connections,
            )
            return

        self._layout_gate(
            operation=operation,
            metrics=metrics,
            column=column,
            x=x,
            style=style,
            wire_positions=wire_positions,
            gates=gates,
            gate_annotations=gate_annotations,
            connections=connections,
        )

    def _append_classical_condition_connections(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        anchor_center_y: float,
        anchor_half_extent: float,
        wire_positions: dict[str, float],
        connections: list[SceneConnection],
    ) -> None:
        for anchor in iter_classical_condition_anchors(operation.classical_conditions):
            wire_y = wire_positions[anchor.wire_id]
            direction = 1.0 if wire_y >= anchor_center_y else -1.0
            connections.append(
                SceneConnection(
                    column=column,
                    x=x,
                    y_start=wire_y,
                    y_end=anchor_center_y + (direction * anchor_half_extent),
                    is_classical=True,
                    double_line=True,
                    linestyle="solid",
                    arrow_at_end=True,
                    label=anchor.label,
                )
            )

    def _layout_measurement(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
        style: DrawStyle,
        wire_map: dict[str, WireIR],
        wire_positions: dict[str, float],
        connections: list[SceneConnection],
        measurements: list[SceneMeasurement],
    ) -> None:
        quantum_y = wire_positions[operation.target_wires[0]]
        classical_target = (
            operation.classical_target
            if isinstance(operation, MeasurementIR) and operation.classical_target is not None
            else None
        )
        classical_y = wire_positions.get(classical_target) if classical_target is not None else None
        classical_label = None
        if classical_target is not None:
            classical_wire = wire_map.get(classical_target)
            classical_label = (
                str(operation.metadata.get("classical_bit_label"))
                if operation.metadata.get("classical_bit_label") is not None
                else getattr(classical_wire, "label", None) or classical_target
            )
        connector_x = x + metrics.width * 0.24
        connector_y = quantum_y + style.gate_height * 0.18
        measurements.append(
            SceneMeasurement(
                column=column,
                x=x,
                quantum_y=quantum_y,
                classical_y=classical_y,
                width=metrics.width,
                height=style.gate_height,
                label=operation.label or "M",
                connector_x=connector_x,
                connector_y=connector_y,
            )
        )
        if classical_y is not None:
            connections.append(
                SceneConnection(
                    column=column,
                    x=connector_x,
                    y_start=connector_y,
                    y_end=classical_y,
                    is_classical=True,
                    linestyle="dashed",
                    arrow_at_end=True,
                    label=classical_label,
                )
            )

    def _layout_barrier(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        wire_positions: dict[str, float],
        barriers: list[SceneBarrier],
    ) -> None:
        y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
        barriers.append(
            SceneBarrier(column=column, x=x, y_top=y_top - 0.3, y_bottom=y_bottom + 0.3)
        )

    def _layout_swap(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        style: DrawStyle,
        wire_positions: dict[str, float],
        connections: list[SceneConnection],
        swaps: list[SceneSwap],
    ) -> None:
        y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
        connections.append(SceneConnection(column=column, x=x, y_start=y_top, y_end=y_bottom))
        swaps.append(
            SceneSwap(
                column=column,
                x=x,
                y_top=y_top,
                y_bottom=y_bottom,
                marker_size=style.swap_marker_size,
            )
        )
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=(y_top + y_bottom) / 2,
            anchor_half_extent=style.swap_marker_size,
            wire_positions=wire_positions,
            connections=connections,
        )

    def _layout_controlled_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
        style: DrawStyle,
        wire_positions: dict[str, float],
        gates: list[SceneGate],
        gate_annotations: list[SceneGateAnnotation],
        controls: list[SceneControl],
        connections: list[SceneConnection],
    ) -> None:
        if self._uses_canonical_controlled_z(operation):
            self._layout_controlled_z(
                operation=operation,
                column=column,
                x=x,
                style=style,
                wire_positions=wire_positions,
                controls=controls,
                connections=connections,
            )
            return

        if self._uses_canonical_controlled_x_target(operation):
            self._layout_controlled_x(
                operation=operation,
                column=column,
                x=x,
                style=style,
                wire_positions=wire_positions,
                gates=gates,
                controls=controls,
                connections=connections,
            )
            return

        y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
        gate_y = (y_top + y_bottom) / 2
        gates.append(
            SceneGate(
                column=column,
                x=x,
                y=gate_y,
                width=metrics.width,
                height=max(style.gate_height, (y_bottom - y_top) + style.gate_height),
                label=metrics.display_label,
                subtitle=metrics.subtitle,
                kind=operation.kind,
                render_style=GateRenderStyle.BOX,
            )
        )
        self._append_gate_annotations(
            column=column,
            x=x,
            width=metrics.width,
            style=style,
            target_wires=operation.target_wires,
            wire_positions=wire_positions,
            gate_annotations=gate_annotations,
        )
        control_ids = operation.control_wires
        for control_id in control_ids:
            controls.append(SceneControl(column=column, x=x, y=wire_positions[control_id]))
        span_top, span_bottom = vertical_span(
            wire_positions, (*control_ids, *operation.target_wires)
        )
        connections.append(SceneConnection(column=column, x=x, y_start=span_top, y_end=span_bottom))
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=gate_y,
            anchor_half_extent=max(style.gate_height, (y_bottom - y_top) + style.gate_height) / 2,
            wire_positions=wire_positions,
            connections=connections,
        )

    def _layout_controlled_z(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        style: DrawStyle,
        wire_positions: dict[str, float],
        controls: list[SceneControl],
        connections: list[SceneConnection],
    ) -> None:
        control_ids = (*operation.control_wires, *operation.target_wires)
        for control_id in control_ids:
            controls.append(SceneControl(column=column, x=x, y=wire_positions[control_id]))
        span_top, span_bottom = vertical_span(wire_positions, control_ids)
        connections.append(SceneConnection(column=column, x=x, y_start=span_top, y_end=span_bottom))
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=wire_positions[operation.target_wires[0]],
            anchor_half_extent=style.control_radius,
            wire_positions=wire_positions,
            connections=connections,
        )

    def _layout_controlled_x(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        style: DrawStyle,
        wire_positions: dict[str, float],
        gates: list[SceneGate],
        controls: list[SceneControl],
        connections: list[SceneConnection],
    ) -> None:
        target_wire = operation.target_wires[0]
        target_y = wire_positions[target_wire]
        gates.append(
            SceneGate(
                column=column,
                x=x,
                y=target_y,
                width=style.gate_height,
                height=style.gate_height,
                label="X",
                subtitle=None,
                kind=operation.kind,
                render_style=GateRenderStyle.X_TARGET,
            )
        )
        for control_id in operation.control_wires:
            controls.append(SceneControl(column=column, x=x, y=wire_positions[control_id]))
        span_top, span_bottom = vertical_span(
            wire_positions, (*operation.control_wires, target_wire)
        )
        connections.append(SceneConnection(column=column, x=x, y_start=span_top, y_end=span_bottom))
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=target_y,
            anchor_half_extent=style.gate_height * 0.36,
            wire_positions=wire_positions,
            connections=connections,
        )

    def _layout_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
        style: DrawStyle,
        wire_positions: dict[str, float],
        gates: list[SceneGate],
        gate_annotations: list[SceneGateAnnotation],
        connections: list[SceneConnection],
    ) -> None:
        y_top, y_bottom = vertical_span(wire_positions, operation.target_wires)
        gates.append(
            SceneGate(
                column=column,
                x=x,
                y=(y_top + y_bottom) / 2,
                width=metrics.width,
                height=max(style.gate_height, (y_bottom - y_top) + style.gate_height),
                label=metrics.display_label,
                subtitle=metrics.subtitle,
                kind=operation.kind,
                render_style=GateRenderStyle.BOX,
            )
        )
        self._append_gate_annotations(
            column=column,
            x=x,
            width=metrics.width,
            style=style,
            target_wires=operation.target_wires,
            wire_positions=wire_positions,
            gate_annotations=gate_annotations,
        )
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=(y_top + y_bottom) / 2,
            anchor_half_extent=max(style.gate_height, (y_bottom - y_top) + style.gate_height) / 2,
            wire_positions=wire_positions,
            connections=connections,
        )

    def _uses_canonical_controlled_x_target(self, operation: OperationIR) -> bool:
        return (
            operation.canonical_family is CanonicalGateFamily.X
            and len(operation.target_wires) == 1
            and not operation.parameters
        )

    def _uses_canonical_controlled_z(self, operation: OperationIR) -> bool:
        return (
            operation.canonical_family is CanonicalGateFamily.Z
            and len(operation.target_wires) == 1
            and not operation.parameters
        )

    def _append_gate_annotations(
        self,
        *,
        column: int,
        x: float,
        width: float,
        style: DrawStyle,
        target_wires: Sequence[str],
        wire_positions: dict[str, float],
        gate_annotations: list[SceneGateAnnotation],
    ) -> None:
        if len(target_wires) <= 1:
            return

        annotation_x = x - (width / 2) + min(0.16, width * 0.18)
        for target_index, wire_id in enumerate(target_wires):
            gate_annotations.append(
                SceneGateAnnotation(
                    column=column,
                    x=annotation_x,
                    y=wire_positions[wire_id],
                    text=str(target_index),
                    font_size=style.font_size * 0.56,
                )
            )
