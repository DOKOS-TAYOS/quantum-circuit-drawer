"""3D layout engine that places circuits on chip-inspired topologies."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from ..ir.circuit import CircuitIR, LayerIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind, binary_control_states
from ..ir.wires import WireKind
from ..style import DrawStyle, normalize_style
from ..topology import TopologyInput, TopologyQubitMode, TopologyResizeMode
from ._engine_3d_classical import append_classical_condition_connections_3d
from ._engine_3d_metrics import _OperationMetrics3D, build_operation_metrics_3d
from ._engine_3d_operations import (
    column_depth_step_3d,
    connection_points_3d,
    fit_gate_text_size_3d,
    gate_cube_size_3d,
    gate_hover_text_3d,
    nearest_anchor_wire_3d,
    point_for_wire_3d,
    uses_canonical_controlled_x_target_3d,
    uses_canonical_controlled_z_3d,
)
from ._engine_3d_topology import (
    build_topology_edges_3d,
    build_topology_nodes_3d,
    build_topology_planes_3d,
    build_wire_texts_3d,
)
from ._layering import normalize_draw_layers
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
    SceneTopologyPlane3D,
    SceneWire3D,
)
from .topology_3d import Topology3D, build_topology

logger = logging.getLogger(__name__)

_WIRE_DEPTH_MARGIN = 0.8
_COLUMN_DEPTH_GAP = 0.12
_CLASSICAL_PLANE_GAP = 2.2
_CLASSICAL_WIRE_SPACING = 1.05
_CONTROL_MARKER_SCALE = 7.4
_SWAP_MARKER_SCALE = 1.25


class LayoutEngine3D:
    """Compute a 3D scene from CircuitIR and a requested topology."""

    def compute(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        topology_name: TopologyInput,
        direct: bool,
        hover_enabled: bool,
        topology_qubits: TopologyQubitMode = "used",
        topology_resize: TopologyResizeMode = "error",
    ) -> LayoutScene3D:
        return self._compute_with_normalized_style(
            circuit,
            normalize_style(style),
            topology_name=topology_name,
            direct=direct,
            hover_enabled=hover_enabled,
            topology_qubits=topology_qubits,
            topology_resize=topology_resize,
        )

    def _compute_with_normalized_style(
        self,
        circuit: CircuitIR,
        style: DrawStyle,
        *,
        topology_name: TopologyInput,
        direct: bool,
        hover_enabled: bool,
        topology_qubits: TopologyQubitMode = "used",
        topology_resize: TopologyResizeMode = "error",
    ) -> LayoutScene3D:
        draw_style = style
        normalized_layers = normalize_draw_layers(circuit)
        topology = build_topology(
            topology_name,
            tuple(circuit.quantum_wires),
            topology_qubits=topology_qubits,
            topology_resize=topology_resize,
        )
        metrics = self._build_operation_metrics(normalized_layers, draw_style)
        gate_depth = self._gate_cube_size(draw_style)
        column_depth_step = self._column_depth_step(draw_style)
        z_start = _WIRE_DEPTH_MARGIN
        z_end = (
            z_start
            + max(gate_depth, len(normalized_layers) * column_depth_step)
            + _WIRE_DEPTH_MARGIN
        )

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
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
            classical_wire_positions=classical_wire_positions,
            z_end=z_end,
        )
        gates: list[SceneGate3D] = []
        markers = self._build_topology_nodes(
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
            draw_style=draw_style,
        )
        connections = self._build_topology_edges(
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
        )
        topology_planes = self._build_topology_planes(
            quantum_wire_positions,
            draw_style=draw_style,
        )
        texts = self._build_wire_texts(
            circuit=circuit,
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
            classical_wire_positions=classical_wire_positions,
            hover_enabled=hover_enabled,
            draw_style=draw_style,
        )

        for column, layer in enumerate(normalized_layers):
            gate_z = z_start + ((column + 1) * column_depth_step)
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
            topology_planes=topology_planes,
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

    def _build_operation_metrics(
        self,
        layers: Sequence[LayerIR],
        style: DrawStyle,
    ) -> dict[int, _OperationMetrics3D]:
        return build_operation_metrics_3d(layers, style)

    def _build_wires(
        self,
        *,
        circuit: CircuitIR,
        topology: Topology3D,
        quantum_wire_positions: dict[str, Point3D],
        classical_wire_positions: dict[str, Point3D],
        z_end: float,
    ) -> tuple[SceneWire3D, ...]:
        wires: list[SceneWire3D] = []
        for wire in topology.nodes:
            start = quantum_wire_positions[wire.wire_id]
            wires.append(
                SceneWire3D(
                    id=wire.wire_id,
                    label=wire.label or wire.wire_id,
                    kind=WireKind.QUANTUM,
                    start=start,
                    end=Point3D(x=start.x, y=start.y, z=z_end),
                    hover_text=wire.label or wire.wire_id,
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
        topology: Topology3D,
        quantum_wire_positions: dict[str, Point3D],
        draw_style: DrawStyle,
    ) -> list[SceneMarker3D]:
        return build_topology_nodes_3d(
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
            draw_style=draw_style,
        )

    def _build_topology_edges(
        self,
        *,
        topology: Topology3D,
        quantum_wire_positions: dict[str, Point3D],
    ) -> list[SceneConnection3D]:
        return build_topology_edges_3d(
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
        )

    def _build_topology_planes(
        self,
        quantum_wire_positions: dict[str, Point3D],
        *,
        draw_style: DrawStyle,
    ) -> tuple[SceneTopologyPlane3D, ...]:
        return build_topology_planes_3d(
            quantum_wire_positions,
            draw_style=draw_style,
        )

    def _build_wire_texts(
        self,
        *,
        circuit: CircuitIR,
        topology: Topology3D,
        quantum_wire_positions: dict[str, Point3D],
        classical_wire_positions: dict[str, Point3D],
        hover_enabled: bool,
        draw_style: DrawStyle,
    ) -> list[SceneText3D]:
        return build_wire_texts_3d(
            circuit=circuit,
            topology=topology,
            quantum_wire_positions=quantum_wire_positions,
            classical_wire_positions=classical_wire_positions,
            hover_enabled=hover_enabled,
            draw_style=draw_style,
        )

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
                        operation_id=_operation_id_3d(operation),
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
            draw_style=draw_style,
        )
        if gate is not None:
            gates.append(gate)
            if not hover_enabled and gate.label:
                gate_text = gate.label if not gate.subtitle else f"{gate.label}\n{gate.subtitle}"
                label_font_size = self._fit_gate_text_size(
                    text=gate_text,
                    gate_size=gate.size_x,
                    default_font_size=draw_style.font_size,
                )
                texts.append(
                    SceneText3D(
                        position=Point3D(
                            x=gate.center.x,
                            y=gate.center.y,
                            z=gate.center.z + (gate.size_z * 0.5),
                        ),
                        text=gate_text,
                        font_size=label_font_size,
                        role="gate_label_block" if gate.subtitle else "label",
                        operation_id=_operation_id_3d(operation),
                    )
                )

        if operation.kind is OperationKind.CONTROLLED_GATE:
            simple_binary_states = binary_control_states(operation)
            anchor_wire_ids = operation.target_wires
            if self._uses_canonical_controlled_z(operation):
                anchor_wire_ids = (*operation.control_wires[:1], *operation.target_wires)
            for control_index, control_wire_id in enumerate(operation.control_wires):
                control_point = self._point_for_wire(
                    control_wire_id, quantum_wire_positions, gate_z
                )
                markers.append(
                    SceneMarker3D(
                        column=column,
                        center=control_point,
                        style=MarkerStyle3D.CONTROL,
                        size=draw_style.control_radius * _CONTROL_MARKER_SCALE,
                        state=(
                            simple_binary_states[control_index]
                            if simple_binary_states is not None
                            else 1
                        ),
                        operation_id=_operation_id_3d(operation),
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
                        operation_id=_operation_id_3d(operation),
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
                        size=draw_style.control_radius * _CONTROL_MARKER_SCALE,
                        state=1,
                        operation_id=_operation_id_3d(operation),
                    )
                )
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
        gate_size = self._gate_cube_size(draw_style)
        label = "" if hover_enabled else metrics.display_label
        subtitle = None if hover_enabled else metrics.subtitle
        gates.append(
            SceneGate3D(
                column=column,
                center=target_point,
                size_x=gate_size,
                size_y=gate_size,
                size_z=gate_size,
                label=label,
                subtitle=subtitle,
                kind=OperationKind.MEASUREMENT,
                render_style=GateRenderStyle3D.MEASUREMENT,
                hover_text=self._gate_hover_text(metrics),
                target_positions=(target_point,),
                operation_id=_operation_id_3d(operation),
            )
        )
        if not hover_enabled and label:
            gate_text = label if not subtitle else f"{label}\n{subtitle}"
            label_font_size = self._fit_gate_text_size(
                text=gate_text,
                gate_size=gate_size,
                default_font_size=draw_style.font_size,
            )
            texts.append(
                SceneText3D(
                    position=Point3D(
                        x=target_point.x,
                        y=target_point.y,
                        z=target_point.z + (gate_size * 0.5),
                    ),
                    text=gate_text,
                    font_size=label_font_size,
                    role="gate_label_block" if subtitle else "label",
                    operation_id=_operation_id_3d(operation),
                )
            )
        if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
            classical_point = classical_wire_positions[operation.classical_target]
            classical_label = (
                str(operation.metadata.get("classical_bit_label"))
                if operation.metadata.get("classical_bit_label") is not None
                else operation.classical_target
            )
            connections.append(
                SceneConnection3D(
                    column=column,
                    points=(
                        Point3D(x=target_point.x, y=target_point.y, z=target_point.z),
                        Point3D(x=classical_point.x, y=classical_point.y, z=target_point.z),
                    ),
                    is_classical=True,
                    arrow_at_end=True,
                    label=classical_label,
                    operation_id=_operation_id_3d(operation),
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
                    size=draw_style.swap_marker_size * _SWAP_MARKER_SCALE,
                    operation_id=_operation_id_3d(operation),
                )
            )
        if len(target_points) == 2:
            connections.append(
                SceneConnection3D(
                    column=column,
                    points=target_points,
                    operation_id=_operation_id_3d(operation),
                )
            )

    def _build_gate(
        self,
        *,
        operation: OperationIR,
        metrics: _OperationMetrics3D,
        column: int,
        target_points: tuple[Point3D, ...],
        hover_enabled: bool,
        draw_style: DrawStyle,
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
        gate_size = self._gate_cube_size(draw_style)
        return SceneGate3D(
            column=column,
            center=Point3D(x=center_x, y=center_y, z=center_z),
            size_x=max(gate_size, span_x + gate_size),
            size_y=max(gate_size, span_y + gate_size),
            size_z=gate_size,
            label=label if render_style is not GateRenderStyle3D.X_TARGET else "",
            subtitle=subtitle if render_style is not GateRenderStyle3D.X_TARGET else None,
            kind=operation.kind,
            render_style=render_style,
            hover_text=self._gate_hover_text(metrics),
            target_positions=target_points,
            operation_id=_operation_id_3d(operation),
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
        append_classical_condition_connections_3d(
            operation=operation,
            column=column,
            gate_center=gate_center,
            classical_wire_positions=classical_wire_positions,
            connections=connections,
        )

    def _point_for_wire(
        self,
        wire_id: str,
        quantum_wire_positions: dict[str, Point3D],
        gate_z: float,
    ) -> Point3D:
        return point_for_wire_3d(wire_id, quantum_wire_positions, gate_z)

    def _nearest_anchor_wire(
        self,
        *,
        control_wire_id: str,
        anchor_wire_ids: Sequence[str],
        topology: Topology3D,
    ) -> str:
        return nearest_anchor_wire_3d(
            control_wire_id=control_wire_id,
            anchor_wire_ids=anchor_wire_ids,
            topology=topology,
        )

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
        return connection_points_3d(
            topology=topology,
            control_wire_id=control_wire_id,
            target_wire_id=target_wire_id,
            control_point=control_point,
            anchor_point=anchor_point,
            direct=direct,
        )

    def _uses_canonical_controlled_x_target(self, operation: OperationIR) -> bool:
        return uses_canonical_controlled_x_target_3d(operation)

    def _uses_canonical_controlled_z(self, operation: OperationIR) -> bool:
        return uses_canonical_controlled_z_3d(operation)

    def _gate_hover_text(self, metrics: _OperationMetrics3D) -> str:
        return gate_hover_text_3d(metrics)

    def _gate_cube_size(self, style: DrawStyle) -> float:
        return gate_cube_size_3d(style)

    def _column_depth_step(self, style: DrawStyle) -> float:
        return column_depth_step_3d(style)

    def _fit_gate_text_size(
        self,
        *,
        text: str,
        gate_size: float,
        default_font_size: float,
    ) -> float:
        return fit_gate_text_size_3d(
            text=text,
            gate_size=gate_size,
            default_font_size=default_font_size,
        )


def _operation_id_3d(operation: OperationIR) -> str | None:
    resolved = operation.metadata.get("semantic_operation_id")
    if isinstance(resolved, str) and resolved:
        return resolved
    return None
