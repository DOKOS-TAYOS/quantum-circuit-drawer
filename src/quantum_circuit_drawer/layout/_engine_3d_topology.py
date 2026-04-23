"""Topology-scene helpers for the 3D layout engine."""

from __future__ import annotations

from ..ir.circuit import CircuitIR
from ..style import DrawStyle
from .scene_3d import (
    ConnectionRenderStyle3D,
    MarkerStyle3D,
    Point3D,
    SceneConnection3D,
    SceneMarker3D,
    SceneText3D,
    SceneTopologyPlane3D,
)
from .topology_3d import Topology3D

_TOPOLOGY_NODE_SIZE = 1.65
_TOPOLOGY_PLANE_ALPHA = 0.105
_TOPOLOGY_PLANE_PADDING = 0.55


def build_topology_nodes_3d(
    *,
    topology: Topology3D,
    quantum_wire_positions: dict[str, Point3D],
    draw_style: DrawStyle,
) -> list[SceneMarker3D]:
    """Build topology-node markers for each quantum wire."""

    return [
        SceneMarker3D(
            column=-1,
            center=quantum_wire_positions[wire.wire_id],
            style=MarkerStyle3D.TOPOLOGY_NODE,
            size=draw_style.control_radius * _TOPOLOGY_NODE_SIZE,
        )
        for wire in topology.nodes
    ]


def build_topology_edges_3d(
    *,
    topology: Topology3D,
    quantum_wire_positions: dict[str, Point3D],
) -> list[SceneConnection3D]:
    """Build topology-edge scene connections."""

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


def build_topology_planes_3d(
    quantum_wire_positions: dict[str, Point3D],
    *,
    draw_style: DrawStyle,
) -> tuple[SceneTopologyPlane3D, ...]:
    """Build the topology plane shown under the quantum-wire positions."""

    x_values = [point.x for point in quantum_wire_positions.values()]
    y_values = [point.y for point in quantum_wire_positions.values()]
    z_start = next(iter(quantum_wire_positions.values())).z
    return (
        SceneTopologyPlane3D(
            x_min=min(x_values) - _TOPOLOGY_PLANE_PADDING,
            x_max=max(x_values) + _TOPOLOGY_PLANE_PADDING,
            y_min=min(y_values) - _TOPOLOGY_PLANE_PADDING,
            y_max=max(y_values) + _TOPOLOGY_PLANE_PADDING,
            z=z_start,
            color=draw_style.theme.topology_plane_color or draw_style.theme.accent_color,
            alpha=_TOPOLOGY_PLANE_ALPHA,
        ),
    )


def build_wire_texts_3d(
    *,
    circuit: CircuitIR,
    topology: Topology3D,
    quantum_wire_positions: dict[str, Point3D],
    classical_wire_positions: dict[str, Point3D],
    hover_enabled: bool,
    draw_style: DrawStyle,
) -> list[SceneText3D]:
    """Build 3D wire labels when hover text is not taking over."""

    if hover_enabled:
        return []

    texts: list[SceneText3D] = []
    for wire in topology.nodes:
        position = quantum_wire_positions[wire.wire_id]
        texts.append(
            SceneText3D(
                position=Point3D(x=position.x, y=position.y + 0.24, z=position.z - 0.35),
                text=wire.label or wire.wire_id,
                font_size=draw_style.font_size * 0.88,
                role="label",
                wire_id=wire.wire_id,
            )
        )
    for wire in circuit.classical_wires:
        position = classical_wire_positions[wire.id]
        texts.append(
            SceneText3D(
                position=Point3D(x=position.x, y=position.y - 0.28, z=position.z - 0.35),
                text=wire.label or wire.id,
                font_size=draw_style.font_size * 0.82,
                role="label",
                wire_id=wire.id,
            )
        )
    return texts
