"""Primitive emitters for operation layout scene building."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from ..ir.measurements import MeasurementIR
from ..ir.operations import (
    CanonicalGateFamily,
    OperationIR,
    OperationKind,
    binary_control_states,
)
from ..utils.formatting import format_gate_name
from ._classical_conditions import iter_classical_condition_anchors
from ._layout_scaffold import _OperationMetrics
from .routing import vertical_span
from .scene import (
    GateRenderStyle,
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGateAnnotation,
    SceneMeasurement,
    SceneSwap,
)

if TYPE_CHECKING:
    from ._operation_layout import _OperationSceneBuilder


def layout_operation(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    metrics: _OperationMetrics,
    column: int,
    x: float,
) -> None:
    if isinstance(operation, MeasurementIR) or operation.kind is OperationKind.MEASUREMENT:
        layout_measurement(builder, operation=operation, metrics=metrics, column=column, x=x)
        return

    if operation.kind is OperationKind.BARRIER:
        layout_barrier(builder, operation=operation, column=column, x=x)
        return

    if operation.kind is OperationKind.SWAP:
        layout_swap(builder, operation=operation, column=column, x=x)
        return

    if operation.kind is OperationKind.CONTROLLED_GATE:
        layout_controlled_gate(builder, operation=operation, metrics=metrics, column=column, x=x)
        return

    layout_gate(builder, operation=operation, metrics=metrics, column=column, x=x)


def append_classical_condition_connections(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    x: float,
    anchor_center_y: float,
    anchor_half_extent: float,
) -> None:
    for anchor in iter_classical_condition_anchors(operation.classical_conditions):
        wire_y = builder.scaffold.wire_positions[anchor.wire_id]
        direction = 1.0 if wire_y >= anchor_center_y else -1.0
        builder.connections.append(
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


def layout_measurement(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    metrics: _OperationMetrics,
    column: int,
    x: float,
) -> None:
    style = builder.scaffold.draw_style
    quantum_y = builder.scaffold.wire_positions[operation.target_wires[0]]
    classical_target = (
        operation.classical_target
        if isinstance(operation, MeasurementIR) and operation.classical_target is not None
        else None
    )
    classical_y = (
        builder.scaffold.wire_positions.get(classical_target)
        if classical_target is not None
        else None
    )
    classical_label = None
    if classical_target is not None:
        classical_wire = builder.wire_map.get(classical_target)
        classical_label = (
            str(operation.metadata.get("classical_bit_label"))
            if operation.metadata.get("classical_bit_label") is not None
            else getattr(classical_wire, "label", None) or classical_target
        )
    connector_x = x + metrics.width * 0.24
    connector_y = quantum_y + style.gate_height * 0.18
    hover_data = builder._maybe_hover_data(
        operation=operation,
        column=column,
        name=builder._hover_name(operation, metrics.display_label),
        gate_x=x,
        gate_y=quantum_y,
        gate_width=metrics.width,
        gate_height=style.gate_height,
    )
    builder.measurements.append(
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
        builder.connections.append(
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


def layout_barrier(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    x: float,
) -> None:
    y_top, y_bottom = vertical_span(builder.scaffold.wire_positions, operation.target_wires)
    builder.barriers.append(
        SceneBarrier(column=column, x=x, y_top=y_top - 0.3, y_bottom=y_bottom + 0.3)
    )


def layout_swap(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    x: float,
) -> None:
    style = builder.scaffold.draw_style
    y_top, y_bottom = vertical_span(builder.scaffold.wire_positions, operation.target_wires)
    hover_data = builder._maybe_hover_data(
        operation=operation,
        column=column,
        name=builder._hover_name(operation, format_gate_name(operation.label or operation.name)),
        gate_x=x,
        gate_y=(y_top + y_bottom) / 2,
        gate_width=style.swap_marker_size * 2.0,
        gate_height=style.swap_marker_size * 2.0,
    )
    builder.connections.append(
        SceneConnection(
            column=column,
            x=x,
            y_start=y_top,
            y_end=y_bottom,
            hover_data=hover_data,
        )
    )
    builder.swaps.append(
        SceneSwap(
            column=column,
            x=x,
            y_top=y_top,
            y_bottom=y_bottom,
            marker_size=style.swap_marker_size,
            hover_data=hover_data,
        )
    )
    append_classical_condition_connections(
        builder,
        operation=operation,
        column=column,
        x=x,
        anchor_center_y=(y_top + y_bottom) / 2,
        anchor_half_extent=style.swap_marker_size,
    )


def layout_controlled_gate(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    metrics: _OperationMetrics,
    column: int,
    x: float,
) -> None:
    if uses_canonical_controlled_z(builder, operation):
        layout_controlled_z(builder, operation=operation, column=column, x=x)
        return

    if uses_canonical_controlled_x_target(builder, operation):
        layout_controlled_x(builder, operation=operation, column=column, x=x)
        return

    style = builder.scaffold.draw_style
    y_top, y_bottom = vertical_span(builder.scaffold.wire_positions, operation.target_wires)
    gate_y = (y_top + y_bottom) / 2
    gate_height = max(style.gate_height, (y_bottom - y_top) + style.gate_height)
    hover_data = builder._maybe_hover_data(
        operation=operation,
        column=column,
        name=builder._hover_name(operation, metrics.display_label),
        gate_x=x,
        gate_y=gate_y,
        gate_width=metrics.width,
        gate_height=gate_height,
    )
    builder.gates.append(
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
    append_gate_annotations(
        builder,
        column=column,
        x=x,
        width=metrics.width,
        target_wires=operation.target_wires,
    )
    append_semantic_annotations(
        builder,
        operation=operation,
        column=column,
        x=x,
        gate_y=gate_y,
        gate_height=gate_height,
    )
    simple_binary_states = binary_control_states(operation)
    for control_index, control_id in enumerate(operation.control_wires):
        builder.controls.append(
            SceneControl(
                column=column,
                x=x,
                y=builder.scaffold.wire_positions[control_id],
                state=(
                    simple_binary_states[control_index] if simple_binary_states is not None else 1
                ),
                hover_data=hover_data,
            )
        )
    span_top, span_bottom = vertical_span(
        builder.scaffold.wire_positions,
        (*operation.control_wires, *operation.target_wires),
    )
    builder.connections.append(
        SceneConnection(
            column=column,
            x=x,
            y_start=span_top,
            y_end=span_bottom,
            hover_data=hover_data,
        )
    )
    append_classical_condition_connections(
        builder,
        operation=operation,
        column=column,
        x=x,
        anchor_center_y=gate_y,
        anchor_half_extent=gate_height / 2,
    )


def layout_controlled_z(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    x: float,
) -> None:
    style = builder.scaffold.draw_style
    simple_binary_states = binary_control_states(operation)
    hover_data = builder._maybe_hover_data(
        operation=operation,
        column=column,
        name=builder._hover_name(operation, format_gate_name(operation.label or operation.name)),
        gate_x=x,
        gate_y=builder.scaffold.wire_positions[operation.target_wires[0]],
        gate_width=style.control_radius * 2.0,
        gate_height=style.control_radius * 2.0,
    )
    for control_index, control_id in enumerate(operation.control_wires):
        builder.controls.append(
            SceneControl(
                column=column,
                x=x,
                y=builder.scaffold.wire_positions[control_id],
                state=(
                    simple_binary_states[control_index] if simple_binary_states is not None else 1
                ),
                hover_data=hover_data,
            )
        )
    for target_wire in operation.target_wires:
        builder.controls.append(
            SceneControl(
                column=column,
                x=x,
                y=builder.scaffold.wire_positions[target_wire],
                state=1,
                hover_data=hover_data,
            )
        )
    control_ids = (*operation.control_wires, *operation.target_wires)
    span_top, span_bottom = vertical_span(builder.scaffold.wire_positions, control_ids)
    builder.connections.append(
        SceneConnection(
            column=column,
            x=x,
            y_start=span_top,
            y_end=span_bottom,
            hover_data=hover_data,
        )
    )
    append_classical_condition_connections(
        builder,
        operation=operation,
        column=column,
        x=x,
        anchor_center_y=builder.scaffold.wire_positions[operation.target_wires[0]],
        anchor_half_extent=style.control_radius,
    )


def layout_controlled_x(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    x: float,
) -> None:
    style = builder.scaffold.draw_style
    target_wire = operation.target_wires[0]
    target_y = builder.scaffold.wire_positions[target_wire]
    simple_binary_states = binary_control_states(operation)
    hover_data = builder._maybe_hover_data(
        operation=operation,
        column=column,
        name=builder._hover_name(operation, format_gate_name(operation.label or operation.name)),
        gate_x=x,
        gate_y=target_y,
        gate_width=style.gate_height,
        gate_height=style.gate_height,
    )
    builder.gates.append(
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
    for control_index, control_id in enumerate(operation.control_wires):
        builder.controls.append(
            SceneControl(
                column=column,
                x=x,
                y=builder.scaffold.wire_positions[control_id],
                state=(
                    simple_binary_states[control_index] if simple_binary_states is not None else 1
                ),
                hover_data=hover_data,
            )
        )
    span_top, span_bottom = vertical_span(
        builder.scaffold.wire_positions,
        (*operation.control_wires, target_wire),
    )
    builder.connections.append(
        SceneConnection(
            column=column,
            x=x,
            y_start=span_top,
            y_end=span_bottom,
            hover_data=hover_data,
        )
    )
    append_classical_condition_connections(
        builder,
        operation=operation,
        column=column,
        x=x,
        anchor_center_y=target_y,
        anchor_half_extent=style.gate_height * 0.36,
    )


def layout_gate(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    metrics: _OperationMetrics,
    column: int,
    x: float,
) -> None:
    style = builder.scaffold.draw_style
    y_top, y_bottom = vertical_span(builder.scaffold.wire_positions, operation.target_wires)
    gate_y = (y_top + y_bottom) / 2
    gate_height = max(style.gate_height, (y_bottom - y_top) + style.gate_height)
    hover_data = builder._maybe_hover_data(
        operation=operation,
        column=column,
        name=builder._hover_name(operation, metrics.display_label),
        gate_x=x,
        gate_y=gate_y,
        gate_width=metrics.width,
        gate_height=gate_height,
    )
    builder.gates.append(
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
    append_gate_annotations(
        builder,
        column=column,
        x=x,
        width=metrics.width,
        target_wires=operation.target_wires,
    )
    append_semantic_annotations(
        builder,
        operation=operation,
        column=column,
        x=x,
        gate_y=gate_y,
        gate_height=gate_height,
    )
    append_classical_condition_connections(
        builder,
        operation=operation,
        column=column,
        x=x,
        anchor_center_y=gate_y,
        anchor_half_extent=gate_height / 2,
    )


def uses_canonical_controlled_x_target(
    builder: _OperationSceneBuilder,
    operation: OperationIR,
) -> bool:
    del builder
    if binary_control_states(operation) is None:
        return False
    return (
        operation.canonical_family is CanonicalGateFamily.X
        and len(operation.target_wires) == 1
        and not operation.parameters
    )


def uses_canonical_controlled_z(
    builder: _OperationSceneBuilder,
    operation: OperationIR,
) -> bool:
    del builder
    if binary_control_states(operation) is None:
        return False
    return (
        operation.canonical_family is CanonicalGateFamily.Z
        and len(operation.target_wires) == 1
        and not operation.parameters
    )


def append_gate_annotations(
    builder: _OperationSceneBuilder,
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
        builder.gate_annotations.append(
            SceneGateAnnotation(
                column=column,
                x=annotation_x,
                y=builder.scaffold.wire_positions[wire_id],
                text=str(target_index),
                font_size=builder.scaffold.draw_style.font_size * 0.56,
            )
        )


def append_semantic_annotations(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    x: float,
    gate_y: float,
    gate_height: float,
) -> None:
    raw_annotations = operation.metadata.get("native_annotations", ())
    if not isinstance(raw_annotations, tuple | list):
        return

    annotation_texts = tuple(str(annotation) for annotation in raw_annotations if str(annotation))
    if not annotation_texts:
        return

    top_y = gate_y - (gate_height / 2.0) - 0.24
    for annotation_index, annotation_text in enumerate(annotation_texts):
        builder.gate_annotations.append(
            SceneGateAnnotation(
                column=column,
                x=x,
                y=top_y - (annotation_index * 0.22),
                text=annotation_text,
                font_size=builder.scaffold.draw_style.font_size * 0.48,
            )
        )
