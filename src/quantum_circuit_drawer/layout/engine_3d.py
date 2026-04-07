"""3D layout engine that places circuits on chip-inspired topologies."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import CanonicalGateFamily, OperationIR, OperationKind
from ..style import DrawStyle, normalize_style
from ._classical_conditions import iter_classical_condition_anchors
from ._layering import normalize_draw_layers
from ._operation_text import build_operation_text_metrics
from .scene_3d import (
    ConnectionRenderStyle3D,
    GateRenderStyle3D,
    LayoutScene3D,
    MarkerStyle3D,
    Point3D,
    SceneConnection3D,
    SceneGate3D,
    SceneMarker3D,
    SceneText3D,
    SceneWire3D,
)
from .topology_3d import Topology3D, TopologyName, build_topology

logger = logging.getLogger(__name__)

_WIRE_DEPTH_MARGIN = 0.8
_Z_STEP = 1.6
_CLASSICAL_PLANE_GAP = 2.2
_CLASSICAL_WIRE_SPACING = 1.05
_GATE_SIZE = 0.72
_GATE_DEPTH = 0.72
_TOPOLOGY_NODE_SIZE = 1.65


@dataclass(frozen=True, slots=True)
class _OperationMetrics3D:
    label: str
    display_label: str
    subtitle: str | None


class LayoutEngine3D:
    """Compute a 3D scene from CircuitIR and a requested topology."""

    def compute(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        topology_name: TopologyName,
        direct: bool,
        hover_enabled: bool,
    ) -> LayoutScene3D:
        draw_style = normalize_style(style)
        normalized_layers = normalize_draw_layers(circuit)
        topology = build_topology(topology_name, tuple(circuit.quantum_wires))
        metrics = self._build_operation_metrics(normalized_layers, draw_style)
        gate_depth = max(_GATE_DEPTH, draw_style.gate_height)
        z_start = _WIRE_DEPTH_MARGIN
        z_end = z_start + max(gate_depth, len(normalized_layers) * _Z_STEP) + _WIRE_DEPTH_MARGIN

        quantum_wire_positions = {
            wire_id: Point3D(x=position[0], y=position[1], z=z_start)
            for wire_id, position in topology.positions.items()
        }
        classical_plane_y = (
            min(position.y for position in quantum_wire_positions.values()) - _CLASSICAL_PLANE_GAP
        )
        min_x = min(position.x for position in quantum_wire_positions.values())
        classical_wire_positions = {
            wire.id: Point3D(
                x=min_x + (index * _CLASSICAL_WIRE_SPACING),
                y=classical_plane_y,
                z=z_start,
            )
            for index, wire in enumerate(circuit.classical_wires)
        }

        wires = self._build_wires(
            circuit=circuit,
            quantum_wire_positions=quantum_wire_positions,
            classical_wire_positions=classical_wire_positions,
            z_end=z_end,
        )
        gates: list[SceneGate3D] = []
        markers = self._build_topology_nodes(
            circuit=circuit,
            quantum_wire_positions=quantum_wire_positions,
            draw_style=draw_style,
        )
        connections = self._build_topology_edges(
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
        )
        texts = self._build_wire_texts(
            circuit=circuit,
            quantum_wire_positions=quantum_wire_positions,
            classical_wire_positions=classical_wire_positions,
            hover_enabled=hover_enabled,
            draw_style=draw_style,
        )

        for column, layer in enumerate(normalized_layers):
            gate_z = z_start + ((column + 1) * _Z_STEP)
            for operation in layer.operations:
                self._layout_operation(
                    operation=operation,
                    metrics=metrics[id(operation)],
                    column=column,
                    gate_z=gate_z,
                    topology=topology,
                    direct=direct,
                    hover_enabled=hover_enabled,
                    classical_wire_positions=classical_wire_positions,
                    quantum_wire_positions=quantum_wire_positions,
                    draw_style=draw_style,
                    gates=gates,
                    markers=markers,
                    connections=connections,
                    texts=texts,
                )

        width = (
            max(point.x for point in quantum_wire_positions.values())
            - min(point.x for point in quantum_wire_positions.values())
        ) + 4.0
        height = (
            max(point.y for point in quantum_wire_positions.values()) - classical_plane_y
        ) + 4.0
        scene = LayoutScene3D(
            width=width,
            height=height,
            depth=z_end + _WIRE_DEPTH_MARGIN,
            style=draw_style,
            topology=topology,
            wires=tuple(wires),
            gates=tuple(gates),
            markers=tuple(markers),
            connections=tuple(connections),
            texts=tuple(texts),
            hover_enabled=hover_enabled,
            quantum_wire_positions=quantum_wire_positions,
            classical_wire_positions=classical_wire_positions,
            classical_plane_y=classical_plane_y,
        )
        logger.debug(
            "Computed 3D layout scene for topology=%s wires=%d layers=%d depth=%.2f",
            topology.name,
            circuit.quantum_wire_count,
            len(normalized_layers),
            scene.depth,
        )
        return scene

    def _normalize_layers(self, circuit: CircuitIR) -> tuple[LayerIR, ...]:
        return normalize_draw_layers(circuit)

    def _build_operation_metrics(
        self,
        layers: Sequence[LayerIR],
        style: DrawStyle,
    ) -> dict[int, _OperationMetrics3D]:
        text_metrics = build_operation_text_metrics(layers, style)
        metrics: dict[int, _OperationMetrics3D] = {}
        for layer in layers:
            for operation in layer.operations:
                operation_text = text_metrics[id(operation)]
                metrics[id(operation)] = _OperationMetrics3D(
                    label=operation_text.label,
                    display_label=operation_text.display_label,
                    subtitle=operation_text.subtitle,
                )
        return metrics

    def _build_wires(
        self,
        *,
        circuit: CircuitIR,
        quantum_wire_positions: dict[str, Point3D],
        classical_wire_positions: dict[str, Point3D],
        z_end: float,
    ) -> tuple[SceneWire3D, ...]:
        wires: list[SceneWire3D] = []
        for wire in circuit.quantum_wires:
            start = quantum_wire_positions[wire.id]
            wires.append(
                SceneWire3D(
                    id=wire.id,
                    label=wire.label or wire.id,
                    kind=wire.kind,
                    start=start,
                    end=Point3D(x=start.x, y=start.y, z=z_end),
                    hover_text=wire.label or wire.id,
                )
            )
        for wire in circuit.classical_wires:
            start = classical_wire_positions[wire.id]
            wires.append(
                SceneWire3D(
                    id=wire.id,
                    label=wire.label or wire.id,
                    kind=wire.kind,
                    start=start,
                    end=Point3D(x=start.x, y=start.y, z=z_end),
                    double_line=True,
                    hover_text=wire.label or wire.id,
                )
            )
        return tuple(wires)

    def _build_topology_nodes(
        self,
        *,
        circuit: CircuitIR,
        quantum_wire_positions: dict[str, Point3D],
        draw_style: DrawStyle,
    ) -> list[SceneMarker3D]:
        return [
            SceneMarker3D(
                column=-1,
                center=quantum_wire_positions[wire.id],
                style=MarkerStyle3D.TOPOLOGY_NODE,
                size=draw_style.control_radius * _TOPOLOGY_NODE_SIZE,
            )
            for wire in circuit.quantum_wires
        ]

    def _build_topology_edges(
        self,
        *,
        topology: Topology3D,
        quantum_wire_positions: dict[str, Point3D],
    ) -> list[SceneConnection3D]:
        return [
            SceneConnection3D(
                column=-1,
                points=(
                    quantum_wire_positions[first_wire_id],
                    quantum_wire_positions[second_wire_id],
                ),
                render_style=ConnectionRenderStyle3D.TOPOLOGY_EDGE,
            )
            for first_wire_id, second_wire_id in topology.edges
        ]

    def _build_wire_texts(
        self,
        *,
        circuit: CircuitIR,
        quantum_wire_positions: dict[str, Point3D],
        classical_wire_positions: dict[str, Point3D],
        hover_enabled: bool,
        draw_style: DrawStyle,
    ) -> list[SceneText3D]:
        if hover_enabled:
            return []

        texts: list[SceneText3D] = []
        for wire in circuit.quantum_wires:
            position = quantum_wire_positions[wire.id]
            texts.append(
                SceneText3D(
                    position=Point3D(x=position.x, y=position.y + 0.24, z=position.z - 0.35),
                    text=wire.label or wire.id,
                    font_size=draw_style.font_size * 0.88,
                )
            )
        for wire in circuit.classical_wires:
            position = classical_wire_positions[wire.id]
            texts.append(
                SceneText3D(
                    position=Point3D(x=position.x, y=position.y - 0.28, z=position.z - 0.35),
                    text=wire.label or wire.id,
                    font_size=draw_style.font_size * 0.82,
                )
            )
        return texts

    def _layout_operation(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics3D,
        column: int,
        gate_z: float,
        topology: Topology3D,
        direct: bool,
        hover_enabled: bool,
        classical_wire_positions: dict[str, Point3D],
        quantum_wire_positions: dict[str, Point3D],
        draw_style: DrawStyle,
        gates: list[SceneGate3D],
        markers: list[SceneMarker3D],
        connections: list[SceneConnection3D],
        texts: list[SceneText3D],
    ) -> None:
        if isinstance(operation, MeasurementIR) or operation.kind is OperationKind.MEASUREMENT:
            self._layout_measurement(
                operation=operation,
                metrics=metrics,
                column=column,
                gate_z=gate_z,
                hover_enabled=hover_enabled,
                classical_wire_positions=classical_wire_positions,
                quantum_wire_positions=quantum_wire_positions,
                draw_style=draw_style,
                gates=gates,
                connections=connections,
                texts=texts,
            )
            return

        if operation.kind is OperationKind.SWAP:
            self._layout_swap(
                operation=operation,
                column=column,
                gate_z=gate_z,
                quantum_wire_positions=quantum_wire_positions,
                draw_style=draw_style,
                markers=markers,
                connections=connections,
            )
            return

        if operation.kind is OperationKind.BARRIER:
            barrier_points = [
                self._point_for_wire(wire_id, quantum_wire_positions, gate_z)
                for wire_id in operation.target_wires
            ]
            barrier_points = sorted(barrier_points, key=lambda point: point.y)
            if len(barrier_points) >= 2:
                connections.append(
                    SceneConnection3D(
                        column=column,
                        points=(barrier_points[0], barrier_points[-1]),
                        label="barrier",
                    )
                )
            return

        target_points = tuple(
            self._point_for_wire(wire_id, quantum_wire_positions, gate_z)
            for wire_id in operation.target_wires
        )
        gate = self._build_gate(
            operation=operation,
            metrics=metrics,
            column=column,
            target_points=target_points,
            hover_enabled=hover_enabled,
        )
        if gate is not None:
            gates.append(gate)
            if not hover_enabled and gate.label:
                texts.append(
                    SceneText3D(
                        position=Point3D(
                            x=gate.center.x,
                            y=gate.center.y,
                            z=gate.center.z + (gate.size_z * 0.56),
                        ),
                        text=gate.label,
                    )
                )
                if gate.subtitle:
                    texts.append(
                        SceneText3D(
                            position=Point3D(
                                x=gate.center.x,
                                y=gate.center.y - 0.16,
                                z=gate.center.z + (gate.size_z * 0.4),
                            ),
                            text=gate.subtitle,
                            font_size=draw_style.font_size * 0.78,
                        )
                    )

        if operation.kind is OperationKind.CONTROLLED_GATE:
            anchor_wire_ids = operation.target_wires
            if self._uses_canonical_controlled_z(operation):
                anchor_wire_ids = (*operation.control_wires[:1], *operation.target_wires)
            for control_wire_id in operation.control_wires:
                control_point = self._point_for_wire(
                    control_wire_id, quantum_wire_positions, gate_z
                )
                markers.append(
                    SceneMarker3D(
                        column=column,
                        center=control_point,
                        style=MarkerStyle3D.CONTROL,
                        size=draw_style.control_radius * 6.5,
                    )
                )
                candidate_anchor_wire_ids = tuple(
                    wire_id for wire_id in anchor_wire_ids if wire_id != control_wire_id
                )
                if not candidate_anchor_wire_ids:
                    candidate_anchor_wire_ids = tuple(operation.target_wires)
                anchor_wire_id = self._nearest_anchor_wire(
                    control_wire_id=control_wire_id,
                    anchor_wire_ids=candidate_anchor_wire_ids,
                    topology=topology,
                )
                anchor_point = self._point_for_wire(anchor_wire_id, quantum_wire_positions, gate_z)
                connection_points = self._connection_points(
                    topology=topology,
                    control_wire_id=control_wire_id,
                    target_wire_id=anchor_wire_id,
                    control_point=control_point,
                    anchor_point=anchor_point,
                    direct=direct,
                )
                hover_text = None
                if not direct:
                    hover_text = f"{max(0, len(connection_points) - 2)} intermediate qubits"
                connections.append(
                    SceneConnection3D(
                        column=column,
                        points=connection_points,
                        render_style=ConnectionRenderStyle3D.CONTROL,
                        hover_text=hover_text,
                    )
                )
            if self._uses_canonical_controlled_z(operation):
                target_point = self._point_for_wire(
                    operation.target_wires[0],
                    quantum_wire_positions,
                    gate_z,
                )
                markers.append(
                    SceneMarker3D(
                        column=column,
                        center=target_point,
                        style=MarkerStyle3D.CONTROL,
                        size=draw_style.control_radius * 6.5,
                    )
                )
        if gate is not None and gate.render_style is GateRenderStyle3D.X_TARGET:
            return
        self._append_classical_condition_connections(
            operation=operation,
            column=column,
            gate_center=gate.center if gate is not None else target_points[0],
            classical_wire_positions=classical_wire_positions,
            connections=connections,
        )

    def _layout_measurement(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics3D,
        column: int,
        gate_z: float,
        hover_enabled: bool,
        classical_wire_positions: dict[str, Point3D],
        quantum_wire_positions: dict[str, Point3D],
        draw_style: DrawStyle,
        gates: list[SceneGate3D],
        connections: list[SceneConnection3D],
        texts: list[SceneText3D],
    ) -> None:
        target_point = self._point_for_wire(
            operation.target_wires[0], quantum_wire_positions, gate_z
        )
        gates.append(
            SceneGate3D(
                column=column,
                center=target_point,
                size_x=_GATE_SIZE,
                size_y=_GATE_SIZE,
                size_z=_GATE_DEPTH,
                label=metrics.display_label,
                subtitle=metrics.subtitle,
                kind=OperationKind.MEASUREMENT,
                render_style=GateRenderStyle3D.MEASUREMENT,
                hover_text=self._gate_hover_text(metrics),
                target_positions=(target_point,),
            )
        )
        if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
            classical_point = classical_wire_positions[operation.classical_target]
            connections.append(
                SceneConnection3D(
                    column=column,
                    points=(
                        Point3D(x=target_point.x, y=target_point.y, z=target_point.z),
                        Point3D(x=classical_point.x, y=classical_point.y, z=target_point.z),
                    ),
                    is_classical=True,
                    label=operation.classical_target,
                )
            )

    def _layout_swap(
        self,
        *,
        operation: OperationIR,
        column: int,
        gate_z: float,
        quantum_wire_positions: dict[str, Point3D],
        draw_style: DrawStyle,
        markers: list[SceneMarker3D],
        connections: list[SceneConnection3D],
    ) -> None:
        target_points = tuple(
            self._point_for_wire(wire_id, quantum_wire_positions, gate_z)
            for wire_id in operation.target_wires
        )
        for point in target_points:
            markers.append(
                SceneMarker3D(
                    column=column,
                    center=point,
                    style=MarkerStyle3D.SWAP,
                    size=draw_style.swap_marker_size * 6.2,
                )
            )
        if len(target_points) == 2:
            connections.append(SceneConnection3D(column=column, points=target_points))

    def _build_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics3D,
        column: int,
        target_points: tuple[Point3D, ...],
        hover_enabled: bool,
    ) -> SceneGate3D | None:
        if operation.kind is OperationKind.CONTROLLED_GATE and self._uses_canonical_controlled_z(
            operation
        ):
            return None

        center_x = sum(point.x for point in target_points) / len(target_points)
        center_y = sum(point.y for point in target_points) / len(target_points)
        center_z = target_points[0].z
        span_x = (
            (max(point.x for point in target_points) - min(point.x for point in target_points))
            if len(target_points) > 1
            else 0.0
        )
        span_y = (
            (max(point.y for point in target_points) - min(point.y for point in target_points))
            if len(target_points) > 1
            else 0.0
        )
        render_style = (
            GateRenderStyle3D.X_TARGET
            if operation.kind is OperationKind.CONTROLLED_GATE
            and self._uses_canonical_controlled_x_target(operation)
            else GateRenderStyle3D.BOX
        )
        label = "" if hover_enabled else metrics.display_label
        subtitle = None if hover_enabled else metrics.subtitle
        return SceneGate3D(
            column=column,
            center=Point3D(x=center_x, y=center_y, z=center_z),
            size_x=max(_GATE_SIZE, span_x + _GATE_SIZE),
            size_y=max(_GATE_SIZE, span_y + _GATE_SIZE),
            size_z=_GATE_DEPTH,
            label=label if render_style is not GateRenderStyle3D.X_TARGET else "",
            subtitle=subtitle if render_style is not GateRenderStyle3D.X_TARGET else None,
            kind=operation.kind,
            render_style=render_style,
            hover_text=self._gate_hover_text(metrics),
            target_positions=target_points,
        )

    def _append_classical_condition_connections(
        self,
        *,
        operation: OperationIR,
        column: int,
        gate_center: Point3D,
        classical_wire_positions: dict[str, Point3D],
        connections: list[SceneConnection3D],
    ) -> None:
        for anchor in iter_classical_condition_anchors(operation.classical_conditions):
            classical_point = classical_wire_positions[anchor.wire_id]
            connections.append(
                SceneConnection3D(
                    column=column,
                    points=(
                        Point3D(x=classical_point.x, y=classical_point.y, z=gate_center.z),
                        gate_center,
                    ),
                    is_classical=True,
                    double_line=True,
                    label=anchor.label,
                )
            )

    def _point_for_wire(
        self,
        wire_id: str,
        quantum_wire_positions: dict[str, Point3D],
        gate_z: float,
    ) -> Point3D:
        point = quantum_wire_positions[wire_id]
        return Point3D(x=point.x, y=point.y, z=gate_z)

    def _nearest_anchor_wire(
        self,
        *,
        control_wire_id: str,
        anchor_wire_ids: Sequence[str],
        topology: Topology3D,
    ) -> str:
        distances = [
            (
                len(topology.shortest_path(control_wire_id, anchor_wire_id)),
                anchor_index,
                anchor_wire_id,
            )
            for anchor_index, anchor_wire_id in enumerate(anchor_wire_ids)
        ]
        return min(distances)[2]

    def _connection_points(
        self,
        *,
        topology: Topology3D,
        control_wire_id: str,
        target_wire_id: str,
        control_point: Point3D,
        anchor_point: Point3D,
        direct: bool,
    ) -> tuple[Point3D, ...]:
        if direct:
            return (control_point, anchor_point)

        path_wire_ids = topology.shortest_path(control_wire_id, target_wire_id)
        points = tuple(
            Point3D(
                x=topology.positions[wire_id][0],
                y=topology.positions[wire_id][1],
                z=control_point.z,
            )
            for wire_id in path_wire_ids
        )
        return points if points[-1] == anchor_point else (*points, anchor_point)

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

    def _gate_hover_text(self, metrics: _OperationMetrics3D) -> str:
        if metrics.subtitle:
            return f"{metrics.display_label}({metrics.subtitle})"
        return metrics.display_label
