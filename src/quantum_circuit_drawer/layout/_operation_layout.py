"""Internal helpers for mapping IR operations into 2D scene primitives."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .._matrix_support import operation_matrix_dimension, resolved_operation_matrix
from ..ir.circuit import CircuitIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from ..ir.wires import WireIR
from ..utils.formatting import format_gate_name
from ._classical_conditions import iter_classical_condition_anchors
from ._layout_scaffold import _LayoutScaffold, _OperationMetrics, bundle_size
from .routing import vertical_span
from .scene import (
    GateRenderStyle,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneHoverData,
    SceneMeasurement,
    SceneSwap,
    SceneText,
    SceneWire,
)


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


@dataclass(slots=True)
class _OperationSceneBuilder:
    circuit: CircuitIR
    scaffold: _LayoutScaffold
    hover_enabled: bool = True
    wire_map: dict[str, WireIR] = field(init=False)
    gates: list[SceneGate] = field(default_factory=list, init=False)
    gate_annotations: list[SceneGateAnnotation] = field(default_factory=list, init=False)
    controls: list[SceneControl] = field(default_factory=list, init=False)
    connections: list[SceneConnection] = field(default_factory=list, init=False)
    swaps: list[SceneSwap] = field(default_factory=list, init=False)
    barriers: list[SceneBarrier] = field(default_factory=list, init=False)
    measurements: list[SceneMeasurement] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.wire_map = self.circuit.wire_map

    def build(self) -> _SceneCollections:
        x_end = self.scaffold.draw_style.margin_left + (
            self.scaffold.pages[0].content_width
            if self.scaffold.pages
            else self.scaffold.draw_style.gate_width
        )
        wires = tuple(
            SceneWire(
                id=wire.id,
                label=wire.label or wire.id,
                kind=wire.kind,
                y=self.scaffold.wire_positions[wire.id],
                x_start=self.scaffold.draw_style.margin_left,
                x_end=x_end,
                bundle_size=bundle_size(wire),
            )
            for wire in self.circuit.all_wires
        )
        texts = self._wire_labels()

        for column, layer in enumerate(self.scaffold.normalized_layers):
            x = self.scaffold.x_centers[column]
            for operation in layer.operations:
                self._layout_operation(
                    operation=operation,
                    metrics=self.scaffold.operation_metrics[id(operation)],
                    column=column,
                    x=x,
                )

        return _SceneCollections(
            wires=wires,
            texts=texts,
            gates=tuple(self.gates),
            gate_annotations=tuple(self.gate_annotations),
            controls=tuple(self.controls),
            connections=tuple(self.connections),
            swaps=tuple(self.swaps),
            barriers=tuple(self.barriers),
            measurements=tuple(self.measurements),
        )

    def _wire_labels(self) -> tuple[SceneText, ...]:
        style = self.scaffold.draw_style
        if not style.show_wire_labels:
            return ()
        return tuple(
            SceneText(
                x=style.margin_left - style.label_margin,
                y=self.scaffold.wire_positions[wire.id],
                text=wire.label or wire.id,
                ha="right",
                font_size=style.font_size,
            )
            for wire in self.circuit.all_wires
        )

    def _hover_data(
        self,
        *,
        operation: OperationIR,
        column: int,
        name: str,
        gate_x: float,
        gate_y: float,
        gate_width: float,
        gate_height: float,
    ) -> SceneHoverData:
        quantum_wire_ids = tuple(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
        other_wire_ids = [
            wire_id
            for condition in operation.classical_conditions
            for wire_id in condition.wire_ids
            if wire_id not in quantum_wire_ids
        ]
        if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
            other_wire_ids.append(operation.classical_target)
        unique_other_wire_ids = tuple(dict.fromkeys(other_wire_ids))
        qubit_labels = tuple(
            (self.wire_map[wire_id].label or self.wire_map[wire_id].id)
            if wire_id in self.wire_map
            else wire_id
            for wire_id in quantum_wire_ids
        )
        measurement_bit_label = (
            str(operation.metadata.get("classical_bit_label"))
            if isinstance(operation, MeasurementIR)
            and operation.classical_target is not None
            and operation.metadata.get("classical_bit_label") is not None
            else None
        )
        other_wire_labels = tuple(
            measurement_bit_label
            if measurement_bit_label is not None
            and isinstance(operation, MeasurementIR)
            and operation.classical_target == wire_id
            else (self.wire_map[wire_id].label or self.wire_map[wire_id].id)
            if wire_id in self.wire_map
            else wire_id
            for wire_id in unique_other_wire_ids
        )
        return SceneHoverData(
            key=f"op-{column}-{id(operation)}",
            name=name,
            qubit_labels=qubit_labels,
            other_wire_labels=other_wire_labels,
            matrix=resolved_operation_matrix(operation),
            matrix_dimension=operation_matrix_dimension(operation),
            gate_x=gate_x,
            gate_y=gate_y,
            gate_width=gate_width,
            gate_height=gate_height,
        )

    def _maybe_hover_data(
        self,
        *,
        operation: OperationIR,
        column: int,
        name: str,
        gate_x: float,
        gate_y: float,
        gate_width: float,
        gate_height: float,
    ) -> SceneHoverData | None:
        if not self.hover_enabled:
            return None
        return self._hover_data(
            operation=operation,
            column=column,
            name=name,
            gate_x=gate_x,
            gate_y=gate_y,
            gate_width=gate_width,
            gate_height=gate_height,
        )

    def _hover_name(self, operation: OperationIR | MeasurementIR, display_name: str) -> str:
        if operation.kind is not OperationKind.CONTROLLED_GATE:
            return display_name
        if operation.label is not None and operation.label != operation.name:
            return format_gate_name(operation.label)

        control_count = len(operation.control_wires)
        if control_count == 1:
            if operation.canonical_family is CanonicalGateFamily.X:
                return "CNOT"
            if operation.canonical_family is CanonicalGateFamily.Z:
                return "CZ"
            return f"C{display_name}"
        if control_count == 2 and operation.canonical_family is CanonicalGateFamily.X:
            return "TOFFOLI"
        return f"{'C' * control_count}{display_name}"

    def _layout_operation(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
    ) -> None:
        if isinstance(operation, MeasurementIR) or operation.kind is OperationKind.MEASUREMENT:
            self._layout_measurement(operation=operation, metrics=metrics, column=column, x=x)
            return

        if operation.kind is OperationKind.BARRIER:
            self._layout_barrier(operation=operation, column=column, x=x)
            return

        if operation.kind is OperationKind.SWAP:
            self._layout_swap(operation=operation, column=column, x=x)
            return

        if operation.kind is OperationKind.CONTROLLED_GATE:
            self._layout_controlled_gate(operation=operation, metrics=metrics, column=column, x=x)
            return

        self._layout_gate(operation=operation, metrics=metrics, column=column, x=x)

    def _append_classical_condition_connections(
        self,
        *,
        operation: OperationIR,
        column: int,
        x: float,
        anchor_center_y: float,
        anchor_half_extent: float,
    ) -> None:
        for anchor in iter_classical_condition_anchors(operation.classical_conditions):
            wire_y = self.scaffold.wire_positions[anchor.wire_id]
            direction = 1.0 if wire_y >= anchor_center_y else -1.0
            self.connections.append(
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
    ) -> None:
        style = self.scaffold.draw_style
        quantum_y = self.scaffold.wire_positions[operation.target_wires[0]]
        classical_target = (
            operation.classical_target
            if isinstance(operation, MeasurementIR) and operation.classical_target is not None
            else None
        )
        classical_y = (
            self.scaffold.wire_positions.get(classical_target)
            if classical_target is not None
            else None
        )
        classical_label = None
        if classical_target is not None:
            classical_wire = self.wire_map.get(classical_target)
            classical_label = (
                str(operation.metadata.get("classical_bit_label"))
                if operation.metadata.get("classical_bit_label") is not None
                else getattr(classical_wire, "label", None) or classical_target
            )
        connector_x = x + metrics.width * 0.24
        connector_y = quantum_y + style.gate_height * 0.18
        hover_data = self._maybe_hover_data(
            operation=operation,
            column=column,
            name=self._hover_name(operation, metrics.display_label),
            gate_x=x,
            gate_y=quantum_y,
            gate_width=metrics.width,
            gate_height=style.gate_height,
        )
        self.measurements.append(
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
                hover_data=hover_data,
            )
        )
        if classical_y is not None:
            self.connections.append(
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

    def _layout_barrier(self, *, operation: OperationIR, column: int, x: float) -> None:
        y_top, y_bottom = vertical_span(self.scaffold.wire_positions, operation.target_wires)
        self.barriers.append(
            SceneBarrier(column=column, x=x, y_top=y_top - 0.3, y_bottom=y_bottom + 0.3)
        )

    def _layout_swap(self, *, operation: OperationIR, column: int, x: float) -> None:
        style = self.scaffold.draw_style
        y_top, y_bottom = vertical_span(self.scaffold.wire_positions, operation.target_wires)
        hover_data = self._maybe_hover_data(
            operation=operation,
            column=column,
            name=self._hover_name(operation, format_gate_name(operation.label or operation.name)),
            gate_x=x,
            gate_y=(y_top + y_bottom) / 2,
            gate_width=style.swap_marker_size * 2.0,
            gate_height=style.swap_marker_size * 2.0,
        )
        self.connections.append(
            SceneConnection(
                column=column,
                x=x,
                y_start=y_top,
                y_end=y_bottom,
                hover_data=hover_data,
            )
        )
        self.swaps.append(
            SceneSwap(
                column=column,
                x=x,
                y_top=y_top,
                y_bottom=y_bottom,
                marker_size=style.swap_marker_size,
                hover_data=hover_data,
            )
        )
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=(y_top + y_bottom) / 2,
            anchor_half_extent=style.swap_marker_size,
        )

    def _layout_controlled_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
    ) -> None:
        if self._uses_canonical_controlled_z(operation):
            self._layout_controlled_z(operation=operation, column=column, x=x)
            return

        if self._uses_canonical_controlled_x_target(operation):
            self._layout_controlled_x(operation=operation, column=column, x=x)
            return

        style = self.scaffold.draw_style
        y_top, y_bottom = vertical_span(self.scaffold.wire_positions, operation.target_wires)
        gate_y = (y_top + y_bottom) / 2
        gate_height = max(style.gate_height, (y_bottom - y_top) + style.gate_height)
        hover_data = self._maybe_hover_data(
            operation=operation,
            column=column,
            name=self._hover_name(operation, metrics.display_label),
            gate_x=x,
            gate_y=gate_y,
            gate_width=metrics.width,
            gate_height=gate_height,
        )
        self.gates.append(
            SceneGate(
                column=column,
                x=x,
                y=gate_y,
                width=metrics.width,
                height=gate_height,
                label=metrics.display_label,
                subtitle=metrics.subtitle,
                kind=operation.kind,
                render_style=GateRenderStyle.BOX,
                hover_data=hover_data,
            )
        )
        self._append_gate_annotations(
            column=column,
            x=x,
            width=metrics.width,
            target_wires=operation.target_wires,
        )
        for control_id in operation.control_wires:
            self.controls.append(
                SceneControl(
                    column=column,
                    x=x,
                    y=self.scaffold.wire_positions[control_id],
                    hover_data=hover_data,
                )
            )
        span_top, span_bottom = vertical_span(
            self.scaffold.wire_positions,
            (*operation.control_wires, *operation.target_wires),
        )
        self.connections.append(
            SceneConnection(
                column=column,
                x=x,
                y_start=span_top,
                y_end=span_bottom,
                hover_data=hover_data,
            )
        )
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=gate_y,
            anchor_half_extent=gate_height / 2,
        )

    def _layout_controlled_z(self, *, operation: OperationIR, column: int, x: float) -> None:
        style = self.scaffold.draw_style
        control_ids = (*operation.control_wires, *operation.target_wires)
        hover_data = self._maybe_hover_data(
            operation=operation,
            column=column,
            name=self._hover_name(operation, format_gate_name(operation.label or operation.name)),
            gate_x=x,
            gate_y=self.scaffold.wire_positions[operation.target_wires[0]],
            gate_width=style.control_radius * 2.0,
            gate_height=style.control_radius * 2.0,
        )
        for control_id in control_ids:
            self.controls.append(
                SceneControl(
                    column=column,
                    x=x,
                    y=self.scaffold.wire_positions[control_id],
                    hover_data=hover_data,
                )
            )
        span_top, span_bottom = vertical_span(self.scaffold.wire_positions, control_ids)
        self.connections.append(
            SceneConnection(
                column=column,
                x=x,
                y_start=span_top,
                y_end=span_bottom,
                hover_data=hover_data,
            )
        )
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=self.scaffold.wire_positions[operation.target_wires[0]],
            anchor_half_extent=style.control_radius,
        )

    def _layout_controlled_x(self, *, operation: OperationIR, column: int, x: float) -> None:
        style = self.scaffold.draw_style
        target_wire = operation.target_wires[0]
        target_y = self.scaffold.wire_positions[target_wire]
        hover_data = self._maybe_hover_data(
            operation=operation,
            column=column,
            name=self._hover_name(operation, format_gate_name(operation.label or operation.name)),
            gate_x=x,
            gate_y=target_y,
            gate_width=style.gate_height,
            gate_height=style.gate_height,
        )
        self.gates.append(
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
                hover_data=hover_data,
            )
        )
        for control_id in operation.control_wires:
            self.controls.append(
                SceneControl(
                    column=column,
                    x=x,
                    y=self.scaffold.wire_positions[control_id],
                    hover_data=hover_data,
                )
            )
        span_top, span_bottom = vertical_span(
            self.scaffold.wire_positions,
            (*operation.control_wires, target_wire),
        )
        self.connections.append(
            SceneConnection(
                column=column,
                x=x,
                y_start=span_top,
                y_end=span_bottom,
                hover_data=hover_data,
            )
        )
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=target_y,
            anchor_half_extent=style.gate_height * 0.36,
        )

    def _layout_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics,
        column: int,
        x: float,
    ) -> None:
        style = self.scaffold.draw_style
        y_top, y_bottom = vertical_span(self.scaffold.wire_positions, operation.target_wires)
        gate_y = (y_top + y_bottom) / 2
        gate_height = max(style.gate_height, (y_bottom - y_top) + style.gate_height)
        hover_data = self._maybe_hover_data(
            operation=operation,
            column=column,
            name=self._hover_name(operation, metrics.display_label),
            gate_x=x,
            gate_y=gate_y,
            gate_width=metrics.width,
            gate_height=gate_height,
        )
        self.gates.append(
            SceneGate(
                column=column,
                x=x,
                y=gate_y,
                width=metrics.width,
                height=gate_height,
                label=metrics.display_label,
                subtitle=metrics.subtitle,
                kind=operation.kind,
                render_style=GateRenderStyle.BOX,
                hover_data=hover_data,
            )
        )
        self._append_gate_annotations(
            column=column,
            x=x,
            width=metrics.width,
            target_wires=operation.target_wires,
        )
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            x=x,
            anchor_center_y=gate_y,
            anchor_half_extent=gate_height / 2,
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
        target_wires: Sequence[str],
    ) -> None:
        if len(target_wires) <= 1:
            return

        annotation_x = x - (width / 2) + min(0.16, width * 0.18)
        for target_index, wire_id in enumerate(target_wires):
            self.gate_annotations.append(
                SceneGateAnnotation(
                    column=column,
                    x=annotation_x,
                    y=self.scaffold.wire_positions[wire_id],
                    text=str(target_index),
                    font_size=self.scaffold.draw_style.font_size * 0.56,
                )
            )


def build_scene_collections(
    circuit: CircuitIR,
    scaffold: _LayoutScaffold,
    *,
    hover_enabled: bool = True,
) -> _SceneCollections:
    """Build all scene primitives using the shared scaffold."""

    return _OperationSceneBuilder(
        circuit=circuit,
        scaffold=scaffold,
        hover_enabled=hover_enabled,
    ).build()
