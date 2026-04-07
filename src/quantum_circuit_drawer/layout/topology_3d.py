"""Deterministic chip-topology builders for the 3D circuit view.

Each topology maps the ordered quantum wires of a ``CircuitIR`` onto a fixed
2D footprint that the 3D layout engine then extrudes along circuit depth.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import Literal

from ..ir.wires import WireIR

TopologyName = Literal["line", "grid", "star", "star_tree", "honeycomb"]


@dataclass(frozen=True, slots=True)
class TopologyNode:
    """Planar position assigned to one quantum wire within a topology."""

    wire_id: str
    index: int
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Topology3D:
    """Validated topology definition used by the 3D layout engine."""

    name: TopologyName
    nodes: tuple[TopologyNode, ...]
    edges: tuple[tuple[str, str], ...]

    @property
    def positions(self) -> dict[str, tuple[float, float]]:
        """Return node positions keyed by wire id."""

        return {node.wire_id: (node.x, node.y) for node in self.nodes}

    @property
    def neighbor_map(self) -> dict[str, tuple[str, ...]]:
        """Return the undirected adjacency map implied by ``edges``."""

        neighbors: dict[str, list[str]] = {node.wire_id: [] for node in self.nodes}
        for first, second in self.edges:
            neighbors.setdefault(first, []).append(second)
            neighbors.setdefault(second, []).append(first)
        return {wire_id: tuple(values) for wire_id, values in neighbors.items()}

    def shortest_path(self, start_wire_id: str, end_wire_id: str) -> tuple[str, ...]:
        """Return the shortest wire-id path between two connected topology nodes."""

        if start_wire_id == end_wire_id:
            return (start_wire_id,)

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
                    return next_path
                visited.add(neighbor)
                queue.append((neighbor, next_path))
        raise ValueError(f"topology path not found between {start_wire_id!r} and {end_wire_id!r}")


def build_topology(topology: TopologyName, quantum_wires: tuple[WireIR, ...]) -> Topology3D:
    """Build a validated topology for the provided wire ordering.

    The supported topology names intentionally encode real constraints:
    ``grid`` needs a rectangular factorization, ``star`` needs at least two
    wires, ``star_tree`` only accepts sizes of the form ``3 * 2^d - 2``, and
    ``honeycomb`` is currently defined for 53 wires.
    """

    if topology == "line":
        return _build_line_topology(quantum_wires)
    if topology == "grid":
        return _build_grid_topology(quantum_wires)
    if topology == "star":
        return _build_star_topology(quantum_wires)
    if topology == "star_tree":
        return _build_star_tree_topology(quantum_wires)
    if topology == "honeycomb":
        return _build_honeycomb_topology(quantum_wires)
    raise ValueError(f"unknown topology {topology!r}")


def _unsupported_topology_error(topology: str, wire_count: int) -> ValueError:
    wire_label = "wire" if wire_count == 1 else "wires"
    return ValueError(f"topology '{topology}' does not support {wire_count} quantum {wire_label}")


def _build_line_topology(quantum_wires: tuple[WireIR, ...]) -> Topology3D:
    nodes = tuple(
        TopologyNode(wire_id=wire.id, index=index, x=float(index), y=0.0)
        for index, wire in enumerate(quantum_wires)
    )
    edges = tuple(
        (quantum_wires[index].id, quantum_wires[index + 1].id)
        for index in range(len(quantum_wires) - 1)
    )
    return Topology3D(name="line", nodes=nodes, edges=edges)


def _build_grid_topology(quantum_wires: tuple[WireIR, ...]) -> Topology3D:
    wire_count = len(quantum_wires)
    if wire_count < 4:
        raise _unsupported_topology_error("grid", wire_count)

    factor_pairs = [
        (rows, columns)
        for rows in range(2, int(math.sqrt(wire_count)) + 1)
        if wire_count % rows == 0
        for columns in (wire_count // rows,)
        if columns >= 2
    ]
    if not factor_pairs:
        raise _unsupported_topology_error("grid", wire_count)

    rows, columns = min(
        ((min(first, second), max(first, second)) for first, second in factor_pairs),
        key=lambda pair: (abs(pair[1] - pair[0]), -pair[1]),
    )
    nodes: list[TopologyNode] = []
    edges: list[tuple[str, str]] = []
    for index, wire in enumerate(quantum_wires):
        row = index // columns
        column = index % columns
        nodes.append(TopologyNode(wire_id=wire.id, index=index, x=float(column), y=float(-row)))
        if column > 0:
            edges.append((quantum_wires[index - 1].id, wire.id))
        if row > 0:
            edges.append((quantum_wires[index - columns].id, wire.id))
    return Topology3D(name="grid", nodes=tuple(nodes), edges=tuple(edges))


def _build_star_topology(quantum_wires: tuple[WireIR, ...]) -> Topology3D:
    wire_count = len(quantum_wires)
    if wire_count < 2:
        raise _unsupported_topology_error("star", wire_count)

    center_wire = quantum_wires[0]
    nodes = [TopologyNode(wire_id=center_wire.id, index=0, x=0.0, y=0.0)]
    edges: list[tuple[str, str]] = []
    leaf_count = wire_count - 1
    for leaf_index, wire in enumerate(quantum_wires[1:], start=1):
        angle = (2.0 * math.pi * (leaf_index - 1)) / leaf_count
        nodes.append(
            TopologyNode(
                wire_id=wire.id,
                index=leaf_index,
                x=math.cos(angle) * 2.1,
                y=math.sin(angle) * 2.1,
            )
        )
        edges.append((center_wire.id, wire.id))
    return Topology3D(name="star", nodes=tuple(nodes), edges=tuple(edges))


def _build_star_tree_topology(quantum_wires: tuple[WireIR, ...]) -> Topology3D:
    wire_count = len(quantum_wires)
    if wire_count < 4:
        raise _unsupported_topology_error("star_tree", wire_count)

    depth = _star_tree_depth_for_wire_count(wire_count)
    if depth is None:
        raise _unsupported_topology_error("star_tree", wire_count)

    nodes = [TopologyNode(wire_id=quantum_wires[0].id, index=0, x=0.0, y=0.0)]
    edges: list[tuple[str, str]] = []
    next_wire_index = 1
    branch_angles = (math.pi / 2, 7 * math.pi / 6, 11 * math.pi / 6)
    for branch_angle in branch_angles:
        frontier = [(quantum_wires[0].id, branch_angle, 1)]
        while frontier:
            parent_wire_id, angle, level = frontier.pop(0)
            if next_wire_index >= len(quantum_wires) or level > depth:
                continue

            wire = quantum_wires[next_wire_index]
            next_wire_index += 1
            radius = level * 1.8
            nodes.append(
                TopologyNode(
                    wire_id=wire.id,
                    index=len(nodes),
                    x=math.cos(angle) * radius,
                    y=math.sin(angle) * radius,
                )
            )
            edges.append((parent_wire_id, wire.id))
            if level < depth:
                angle_spread = math.pi / (4 * level)
                frontier.append((wire.id, angle - angle_spread, level + 1))
                frontier.append((wire.id, angle + angle_spread, level + 1))
    return Topology3D(name="star_tree", nodes=tuple(nodes), edges=tuple(edges))


def _star_tree_depth_for_wire_count(wire_count: int) -> int | None:
    depth = 1
    while (3 * (2**depth)) - 2 < wire_count:
        depth += 1
    return depth if (3 * (2**depth)) - 2 == wire_count else None


def _build_honeycomb_topology(quantum_wires: tuple[WireIR, ...]) -> Topology3D:
    if len(quantum_wires) != 53:
        raise _unsupported_topology_error("honeycomb", len(quantum_wires))

    coordinates = {
        0: (2.0, 6.0),
        1: (3.0, 6.0),
        2: (4.0, 6.0),
        3: (5.0, 6.0),
        4: (6.0, 6.0),
        5: (2.0, 5.0),
        6: (6.0, 5.0),
        7: (0.0, 4.0),
        8: (1.0, 4.0),
        9: (2.0, 4.0),
        10: (3.0, 4.0),
        11: (4.0, 4.0),
        12: (5.0, 4.0),
        13: (6.0, 4.0),
        14: (7.0, 4.0),
        15: (8.0, 4.0),
        16: (0.0, 3.0),
        17: (4.0, 3.0),
        18: (8.0, 3.0),
        19: (0.0, 2.0),
        20: (1.0, 2.0),
        21: (2.0, 2.0),
        22: (3.0, 2.0),
        23: (4.0, 2.0),
        24: (5.0, 2.0),
        25: (6.0, 2.0),
        26: (7.0, 2.0),
        27: (8.0, 2.0),
        28: (2.0, 1.0),
        29: (6.0, 1.0),
        30: (0.0, 0.0),
        31: (1.0, 0.0),
        32: (2.0, 0.0),
        33: (3.0, 0.0),
        34: (4.0, 0.0),
        35: (5.0, 0.0),
        36: (6.0, 0.0),
        37: (7.0, 0.0),
        38: (8.0, 0.0),
        39: (0.0, -1.0),
        40: (4.0, -1.0),
        41: (8.0, -1.0),
        42: (0.0, -2.0),
        43: (1.0, -2.0),
        44: (2.0, -2.0),
        45: (3.0, -2.0),
        46: (4.0, -2.0),
        47: (5.0, -2.0),
        48: (6.0, -2.0),
        49: (7.0, -2.0),
        50: (8.0, -2.0),
        51: (2.0, -3.0),
        52: (6.0, -3.0),
    }
    edge_indexes = (
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (0, 5),
        (5, 9),
        (4, 6),
        (6, 13),
        (7, 8),
        (8, 9),
        (9, 10),
        (10, 11),
        (11, 12),
        (12, 13),
        (13, 14),
        (14, 15),
        (7, 16),
        (16, 19),
        (11, 17),
        (17, 23),
        (15, 18),
        (18, 27),
        (19, 20),
        (20, 21),
        (21, 22),
        (22, 23),
        (23, 24),
        (24, 25),
        (25, 26),
        (26, 27),
        (21, 28),
        (28, 32),
        (25, 29),
        (29, 36),
        (30, 31),
        (31, 32),
        (32, 33),
        (33, 34),
        (34, 35),
        (35, 36),
        (36, 37),
        (37, 38),
        (30, 39),
        (39, 42),
        (34, 40),
        (40, 46),
        (38, 41),
        (41, 50),
        (42, 43),
        (43, 44),
        (44, 45),
        (45, 46),
        (46, 47),
        (47, 48),
        (48, 49),
        (49, 50),
        (44, 51),
        (48, 52),
    )
    nodes = tuple(
        TopologyNode(
            wire_id=wire.id,
            index=index,
            x=coordinates[index][0],
            y=coordinates[index][1],
        )
        for index, wire in enumerate(quantum_wires)
    )
    edges = tuple(
        (quantum_wires[first].id, quantum_wires[second].id) for first, second in edge_indexes
    )
    return Topology3D(name="honeycomb", nodes=nodes, edges=edges)
