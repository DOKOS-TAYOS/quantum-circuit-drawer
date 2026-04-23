"""Deterministic chip-topology builders for the 3D circuit view.

Each topology maps the ordered quantum wires of a ``CircuitIR`` onto a fixed
2D footprint that the 3D layout engine then extrudes along circuit depth.
"""

from __future__ import annotations

import math
import re
from collections import deque
from dataclasses import dataclass, field

from ..ir.wires import WireIR
from ..topology import (
    BuiltinTopologyName,
    HardwareNodeId,
    HardwareTopology,
    TopologyInput,
    TopologyQubitMode,
    TopologyResizeMode,
    builtin_topology_names,
    materialize_topology,
    normalize_topology_qubits,
    normalize_topology_resize,
)

TopologyName = BuiltinTopologyName


@dataclass(frozen=True, slots=True)
class TopologyNode:
    """Planar position assigned to one quantum wire within a topology."""

    wire_id: str
    index: int
    x: float
    y: float
    label: str | None = None
    hardware_node_id: HardwareNodeId | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class Topology3D:
    """Validated topology definition used by the 3D layout engine."""

    name: str
    nodes: tuple[TopologyNode, ...]
    edges: tuple[tuple[str, str], ...]
    _positions_cache: dict[str, tuple[float, float]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _neighbor_map_cache: dict[str, tuple[str, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _shortest_path_cache: dict[tuple[str, str], tuple[str, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        positions = {node.wire_id: (node.x, node.y) for node in self.nodes}
        neighbors: dict[str, list[str]] = {node.wire_id: [] for node in self.nodes}
        for first, second in self.edges:
            neighbors.setdefault(first, []).append(second)
            neighbors.setdefault(second, []).append(first)
        object.__setattr__(self, "_positions_cache", positions)
        object.__setattr__(
            self,
            "_neighbor_map_cache",
            {wire_id: tuple(values) for wire_id, values in neighbors.items()},
        )
        object.__setattr__(self, "_shortest_path_cache", {})

    @property
    def positions(self) -> dict[str, tuple[float, float]]:
        """Return node positions keyed by wire id."""

        return self._positions_cache

    @property
    def neighbor_map(self) -> dict[str, tuple[str, ...]]:
        """Return the undirected adjacency map implied by ``edges``."""

        return self._neighbor_map_cache

    def shortest_path(self, start_wire_id: str, end_wire_id: str) -> tuple[str, ...]:
        """Return the shortest wire-id path between two connected topology nodes."""

        if start_wire_id == end_wire_id:
            return (start_wire_id,)

        cache_key = (start_wire_id, end_wire_id)
        cached_path = self._shortest_path_cache.get(cache_key)
        if cached_path is not None:
            return cached_path

        neighbors = self.neighbor_map
        queue: deque[tuple[str, tuple[str, ...]]] = deque([(start_wire_id, (start_wire_id,))])
        visited = {start_wire_id}
        while queue:
            wire_id, path = queue.popleft()
            for neighbor in neighbors.get(wire_id, ()):
                if neighbor in visited:
                    continue
                next_path = (*path, neighbor)
                if neighbor == end_wire_id:
                    self._shortest_path_cache[cache_key] = next_path
                    self._shortest_path_cache[(end_wire_id, start_wire_id)] = tuple(
                        reversed(next_path)
                    )
                    return next_path
                visited.add(neighbor)
                queue.append((neighbor, next_path))
        raise ValueError(
            f"topology '{self.name}' has no path between {start_wire_id!r} and {end_wire_id!r}"
        )


def build_topology(
    topology: TopologyInput,
    quantum_wires: tuple[WireIR, ...],
    *,
    topology_qubits: TopologyQubitMode = "used",
    topology_resize: TopologyResizeMode = "error",
) -> Topology3D:
    """Build a validated topology for the provided wire ordering."""

    concrete_topology = materialize_topology(
        topology,
        qubit_count=len(quantum_wires),
        topology_resize=normalize_topology_resize(topology_resize),
    )
    return _build_custom_topology(
        concrete_topology,
        quantum_wires,
        topology_qubits=normalize_topology_qubits(topology_qubits),
    )


def _build_custom_topology(
    topology: HardwareTopology,
    quantum_wires: tuple[WireIR, ...],
    *,
    topology_qubits: TopologyQubitMode,
) -> Topology3D:
    if len(topology.node_ids) < len(quantum_wires):
        raise ValueError(
            f"topology '{topology.name}' has {len(topology.node_ids)} nodes "
            f"but circuit uses {len(quantum_wires)}"
        )

    coordinates = topology.coordinates or _autolayout_coordinates(
        topology.node_ids,
        topology.edges,
    )
    displayed_node_ids = (
        topology.node_ids if topology_qubits == "all" else topology.node_ids[: len(quantum_wires)]
    )
    displayed_node_id_set = set(displayed_node_ids)
    active_wire_ids = {wire.id for wire in quantum_wires}
    wire_id_by_node_id = {
        node_id: (
            quantum_wires[index].id
            if index < len(quantum_wires)
            else _inactive_topology_wire_id(
                topology_name=topology.name,
                node_id=node_id,
                active_wire_ids=active_wire_ids,
            )
        )
        for index, node_id in enumerate(displayed_node_ids)
    }
    nodes = tuple(
        TopologyNode(
            wire_id=wire_id_by_node_id[node_id],
            index=index,
            x=coordinates[node_id][0],
            y=coordinates[node_id][1],
            label=(
                (quantum_wires[index].label or quantum_wires[index].id)
                if index < len(quantum_wires)
                else str(node_id)
            ),
            hardware_node_id=node_id,
            active=index < len(quantum_wires),
        )
        for index, node_id in enumerate(displayed_node_ids)
    )
    edges = tuple(
        (wire_id_by_node_id[first_node], wire_id_by_node_id[second_node])
        for first_node, second_node in topology.edges
        if first_node in displayed_node_id_set and second_node in displayed_node_id_set
    )
    return Topology3D(name=topology.name, nodes=nodes, edges=edges)


def _inactive_topology_wire_id(
    *,
    topology_name: str,
    node_id: HardwareNodeId,
    active_wire_ids: set[str],
) -> str:
    prefix = _wire_id_slug(topology_name)
    node_slug = _wire_id_slug(str(node_id))
    candidate = f"topology_{prefix}_{node_slug}"
    while candidate in active_wire_ids:
        candidate = f"{candidate}_inactive"
    return candidate


def _wire_id_slug(value: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z_]+", "_", value.strip())
    return slug.strip("_") or "node"


def _autolayout_coordinates(
    node_ids: tuple[str | int, ...],
    edges: tuple[tuple[str | int, str | int], ...],
) -> dict[str | int, tuple[float, float]]:
    if len(node_ids) == 1:
        return {node_ids[0]: (0.0, 0.0)}

    radius = max(1.0, math.sqrt(float(len(node_ids))))
    positions = {
        node_id: (
            radius * math.cos((2.0 * math.pi * index) / len(node_ids)),
            radius * math.sin((2.0 * math.pi * index) / len(node_ids)),
        )
        for index, node_id in enumerate(node_ids)
    }
    k_value = max(1.1, math.sqrt((radius * radius * 4.0) / len(node_ids)))
    edge_list = tuple(edges)
    iterations = 64

    for step in range(iterations):
        displacements = {node_id: [0.0, 0.0] for node_id in node_ids}
        for first_index, first_node in enumerate(node_ids):
            first_x, first_y = positions[first_node]
            for second_node in node_ids[first_index + 1 :]:
                second_x, second_y = positions[second_node]
                delta_x = first_x - second_x
                delta_y = first_y - second_y
                distance = math.hypot(delta_x, delta_y) or 1e-6
                force = (k_value * k_value) / distance
                push_x = (delta_x / distance) * force
                push_y = (delta_y / distance) * force
                displacements[first_node][0] += push_x
                displacements[first_node][1] += push_y
                displacements[second_node][0] -= push_x
                displacements[second_node][1] -= push_y

        for first_node, second_node in edge_list:
            first_x, first_y = positions[first_node]
            second_x, second_y = positions[second_node]
            delta_x = first_x - second_x
            delta_y = first_y - second_y
            distance = math.hypot(delta_x, delta_y) or 1e-6
            force = (distance * distance) / k_value
            pull_x = (delta_x / distance) * force
            pull_y = (delta_y / distance) * force
            displacements[first_node][0] -= pull_x
            displacements[first_node][1] -= pull_y
            displacements[second_node][0] += pull_x
            displacements[second_node][1] += pull_y

        temperature = radius * (0.14 - (0.11 * (step / max(1, iterations - 1))))
        for node_id in node_ids:
            delta_x, delta_y = displacements[node_id]
            distance = math.hypot(delta_x, delta_y)
            if distance <= 0.0:
                continue
            limited_distance = min(distance, temperature)
            current_x, current_y = positions[node_id]
            positions[node_id] = (
                current_x + ((delta_x / distance) * limited_distance),
                current_y + ((delta_y / distance) * limited_distance),
            )

        mean_x = sum(position[0] for position in positions.values()) / len(node_ids)
        mean_y = sum(position[1] for position in positions.values()) / len(node_ids)
        for node_id in node_ids:
            current_x, current_y = positions[node_id]
            positions[node_id] = (current_x - mean_x, current_y - mean_y)

    max_extent = (
        max(max(abs(position[0]), abs(position[1])) for position in positions.values()) or 1.0
    )
    target_extent = max(1.3, math.sqrt(float(len(node_ids))) * 0.95)
    scale = target_extent / max_extent
    return {
        node_id: (round(position[0] * scale, 6), round(position[1] * scale, 6))
        for node_id, position in positions.items()
    }


__all__ = [
    "Topology3D",
    "TopologyName",
    "TopologyNode",
    "build_topology",
    "builtin_topology_names",
]
