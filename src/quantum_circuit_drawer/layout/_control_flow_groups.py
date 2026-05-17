"""Control-flow group highlight helpers for 2D layout scenes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from ..ir.circuit import CircuitIR
from ..ir.classical_conditions import ClassicalConditionIR
from ..ir.wires import WireKind
from ..utils.formatting import format_gate_name
from ._classical_conditions import iter_classical_condition_anchors
from .scene import (
    SceneBarrier,
    SceneConnection,
    SceneControl,
    SceneGate,
    SceneGroupHighlight,
    SceneHoverData,
    SceneMeasurement,
    SceneSwap,
)


@dataclass(slots=True)
class _ControlFlowGroup:
    group_id: str
    label: str
    hover_label: str
    details: tuple[str, ...]
    nesting_depth: int = 0
    conditions: tuple[ClassicalConditionIR, ...] = ()
    operation_ids: set[str] = field(default_factory=set)
    wire_ids: set[str] = field(default_factory=set)


@dataclass(slots=True)
class _ControlFlowBounds:
    start_column: int
    end_column: int
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    def extend(
        self,
        *,
        column: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        self.start_column = min(self.start_column, int(column))
        self.end_column = max(self.end_column, int(column))
        self.x_min = min(self.x_min, float(x_min))
        self.x_max = max(self.x_max, float(x_max))
        self.y_min = min(self.y_min, float(y_min))
        self.y_max = max(self.y_max, float(y_max))


@dataclass(frozen=True, slots=True)
class ControlFlowGroupArtifacts:
    highlights: tuple[SceneGroupHighlight, ...]
    condition_connections: tuple[SceneConnection, ...]


_CONTROL_FLOW_CONDITION_LABEL_NESTING_STEP = 0.14


def build_control_flow_group_artifacts(
    *,
    circuit: CircuitIR,
    wire_y_positions: Mapping[str, float],
    gates: Sequence[SceneGate],
    measurements: Sequence[SceneMeasurement],
    controls: Sequence[SceneControl],
    connections: Sequence[SceneConnection],
    swaps: Sequence[SceneSwap],
    barriers: Sequence[SceneBarrier],
) -> ControlFlowGroupArtifacts:
    """Return one enclosing highlight for every expanded control-flow body."""

    groups, group_ids_by_operation_id = _control_flow_groups_by_operation_id(circuit)
    if not groups:
        return ControlFlowGroupArtifacts(highlights=(), condition_connections=())

    bounds_by_group_id: dict[str, _ControlFlowBounds] = {}
    connection_half_width = 0.08
    barrier_half_width = 0.06
    for gate in gates:
        _extend_group_bounds(
            bounds_by_group_id,
            group_ids_by_operation_id=group_ids_by_operation_id,
            operation_id=gate.operation_id,
            column=gate.column,
            x_min=gate.x - (gate.width / 2.0),
            x_max=gate.x + (gate.width / 2.0),
            y_min=gate.y - (gate.height / 2.0),
            y_max=gate.y + (gate.height / 2.0),
        )
    for measurement in measurements:
        _extend_group_bounds(
            bounds_by_group_id,
            group_ids_by_operation_id=group_ids_by_operation_id,
            operation_id=measurement.operation_id,
            column=measurement.column,
            x_min=measurement.x - (measurement.width / 2.0),
            x_max=measurement.x + (measurement.width / 2.0),
            y_min=measurement.quantum_y - (measurement.height / 2.0),
            y_max=measurement.quantum_y + (measurement.height / 2.0),
        )
    for control in controls:
        _extend_group_bounds(
            bounds_by_group_id,
            group_ids_by_operation_id=group_ids_by_operation_id,
            operation_id=control.operation_id,
            column=control.column,
            x_min=control.x - 0.12,
            x_max=control.x + 0.12,
            y_min=control.y - 0.12,
            y_max=control.y + 0.12,
        )
    for connection in connections:
        if connection.is_classical:
            continue
        _extend_group_bounds(
            bounds_by_group_id,
            group_ids_by_operation_id=group_ids_by_operation_id,
            operation_id=connection.operation_id,
            column=connection.column,
            x_min=connection.x - connection_half_width,
            x_max=connection.x + connection_half_width,
            y_min=min(connection.y_start, connection.y_end),
            y_max=max(connection.y_start, connection.y_end),
        )
    for swap in swaps:
        _extend_group_bounds(
            bounds_by_group_id,
            group_ids_by_operation_id=group_ids_by_operation_id,
            operation_id=swap.operation_id,
            column=swap.column,
            x_min=swap.x - swap.marker_size,
            x_max=swap.x + swap.marker_size,
            y_min=swap.y_top - swap.marker_size,
            y_max=swap.y_bottom + swap.marker_size,
        )
    for barrier in barriers:
        _extend_group_bounds(
            bounds_by_group_id,
            group_ids_by_operation_id=group_ids_by_operation_id,
            operation_id=barrier.operation_id,
            column=barrier.column,
            x_min=barrier.x - barrier_half_width,
            x_max=barrier.x + barrier_half_width,
            y_min=min(barrier.y_top, barrier.y_bottom),
            y_max=max(barrier.y_top, barrier.y_bottom),
        )

    max_nesting_depth = max((group.nesting_depth for group in groups.values()), default=0)
    base_x_padding = 0.16
    base_y_padding = 0.18
    nested_padding_step = 0.08
    highlights: list[SceneGroupHighlight] = []
    condition_connections: list[SceneConnection] = []
    for group_id, bounds in bounds_by_group_id.items():
        group = groups[group_id]
        nesting_extra_padding = nested_padding_step * max(
            0,
            max_nesting_depth - group.nesting_depth,
        )
        x_padding = base_x_padding + nesting_extra_padding
        y_padding = base_y_padding + nesting_extra_padding
        width = (bounds.x_max - bounds.x_min) + (x_padding * 2.0)
        height = (bounds.y_max - bounds.y_min) + (y_padding * 2.0)
        center_x = (bounds.x_min + bounds.x_max) / 2.0
        center_y = (bounds.y_min + bounds.y_max) / 2.0
        highlight = SceneGroupHighlight(
            column=bounds.start_column,
            x=center_x,
            y=center_y,
            width=width,
            height=height,
            label=group.label,
            hover_data=_control_flow_hover_data(
                circuit,
                group=group,
                center_x=center_x,
                center_y=center_y,
                width=width,
                height=height,
            ),
            operation_id=group.group_id,
            start_column=bounds.start_column,
            end_column=bounds.end_column,
            nesting_depth=group.nesting_depth,
        )
        highlights.append(highlight)
        condition_connections.extend(
            _condition_connections_for_group(
                group,
                highlight=highlight,
                wire_y_positions=wire_y_positions,
            )
        )
    sorted_highlights = tuple(
        sorted(highlights, key=lambda highlight: (highlight.column, highlight.x))
    )
    sorted_connections = tuple(
        sorted(condition_connections, key=lambda connection: (connection.column, connection.x))
    )
    return ControlFlowGroupArtifacts(
        highlights=sorted_highlights,
        condition_connections=sorted_connections,
    )


def _control_flow_groups_by_operation_id(
    circuit: CircuitIR,
) -> tuple[dict[str, _ControlFlowGroup], dict[str, tuple[str, ...]]]:
    groups: dict[str, _ControlFlowGroup] = {}
    group_ids_by_operation_id: dict[str, list[str]] = {}
    for layer in circuit.layers:
        for operation in layer.operations:
            operation_id = _string_metadata(operation.metadata, "semantic_operation_id")
            if operation_id is None:
                continue
            for group_metadata, nesting_depth in _control_flow_group_entries(operation.metadata):
                group_id = _string_metadata(group_metadata, "id")
                label = _string_metadata(group_metadata, "label")
                if group_id is None or label is None:
                    continue
                hover_label = _string_metadata(group_metadata, "hover_label") or label
                group = groups.get(group_id)
                if group is None:
                    group = _ControlFlowGroup(
                        group_id=group_id,
                        label=label,
                        hover_label=hover_label,
                        details=_details_metadata(group_metadata),
                        nesting_depth=nesting_depth,
                        conditions=_conditions_metadata(group_metadata),
                    )
                    groups[group_id] = group
                else:
                    group.nesting_depth = min(group.nesting_depth, nesting_depth)
                group.operation_ids.add(operation_id)
                group.wire_ids.update(operation.occupied_wire_ids)
                operation_group_ids = group_ids_by_operation_id.setdefault(operation_id, [])
                if group_id not in operation_group_ids:
                    operation_group_ids.append(group_id)
    return groups, {
        operation_id: tuple(group_ids)
        for operation_id, group_ids in group_ids_by_operation_id.items()
    }


def _control_flow_group_entries(
    metadata: Mapping[str, object],
) -> tuple[tuple[Mapping[str, object], int], ...]:
    stacked_groups = metadata.get("control_flow_groups")
    if isinstance(stacked_groups, Sequence) and not isinstance(stacked_groups, str | bytes):
        groups = tuple(group for group in stacked_groups if isinstance(group, Mapping))
        if groups:
            return tuple((group, depth) for depth, group in enumerate(reversed(groups)))

    group_metadata = _mapping_metadata(metadata, "control_flow_group")
    if group_metadata is None:
        return ()
    return ((group_metadata, 0),)


def _condition_connections_for_group(
    group: _ControlFlowGroup,
    *,
    highlight: SceneGroupHighlight,
    wire_y_positions: Mapping[str, float],
) -> tuple[SceneConnection, ...]:
    connections: list[SceneConnection] = []
    connection_x = highlight.x - (highlight.width / 2.0) + 0.08
    for anchor in iter_classical_condition_anchors(group.conditions):
        wire_y = wire_y_positions.get(anchor.wire_id)
        if wire_y is None:
            continue
        direction = 1.0 if wire_y >= highlight.y else -1.0
        connections.append(
            SceneConnection(
                column=highlight.column,
                x=connection_x,
                y_start=wire_y,
                y_end=highlight.y + (direction * highlight.height / 2.0),
                is_classical=True,
                double_line=True,
                linestyle="solid",
                arrow_at_end=True,
                label=anchor.label,
                label_y_offset=_CONTROL_FLOW_CONDITION_LABEL_NESTING_STEP
                * max(0, group.nesting_depth),
                operation_id=group.group_id,
            )
        )
    return tuple(connections)


def _extend_group_bounds(
    bounds_by_group_id: dict[str, _ControlFlowBounds],
    *,
    group_ids_by_operation_id: dict[str, tuple[str, ...]],
    operation_id: str | None,
    column: int,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
) -> None:
    if operation_id is None:
        return
    group_ids = group_ids_by_operation_id.get(operation_id, ())
    if not group_ids:
        return
    for group_id in group_ids:
        bounds = bounds_by_group_id.get(group_id)
        if bounds is None:
            bounds_by_group_id[group_id] = _ControlFlowBounds(
                start_column=column,
                end_column=column,
                x_min=float(x_min),
                x_max=float(x_max),
                y_min=float(y_min),
                y_max=float(y_max),
            )
            continue
        bounds.extend(column=column, x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max)


def _control_flow_hover_data(
    circuit: CircuitIR,
    *,
    group: _ControlFlowGroup,
    center_x: float,
    center_y: float,
    width: float,
    height: float,
) -> SceneHoverData:
    wire_map = circuit.wire_map
    ordered_wire_ids = tuple(
        wire.id for wire in circuit.all_wires if wire.id in group.wire_ids and wire.id in wire_map
    )
    qubit_labels = tuple(
        wire_map[wire_id].label or wire_id
        for wire_id in ordered_wire_ids
        if wire_map[wire_id].kind is WireKind.QUANTUM
    )
    other_wire_labels = tuple(
        wire_map[wire_id].label or wire_id
        for wire_id in ordered_wire_ids
        if wire_map[wire_id].kind is not WireKind.QUANTUM
    )
    return SceneHoverData(
        key=f"control-flow:{group.group_id}",
        name=format_gate_name(group.hover_label),
        qubit_labels=qubit_labels,
        other_wire_labels=other_wire_labels,
        matrix=None,
        matrix_dimension=None,
        gate_x=center_x,
        gate_y=center_y,
        gate_width=width,
        gate_height=height,
        details=group.details,
    )


def _mapping_metadata(metadata: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = metadata.get(key)
    if isinstance(value, Mapping):
        return value
    return None


def _string_metadata(metadata: Mapping[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _details_metadata(metadata: Mapping[str, object]) -> tuple[str, ...]:
    value = metadata.get("details")
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(entry) for entry in value if str(entry))


def _conditions_metadata(metadata: Mapping[str, object]) -> tuple[ClassicalConditionIR, ...]:
    value = metadata.get("conditions")
    if isinstance(value, ClassicalConditionIR):
        return (value,)
    if not isinstance(value, Sequence):
        return ()
    return tuple(condition for condition in value if isinstance(condition, ClassicalConditionIR))
