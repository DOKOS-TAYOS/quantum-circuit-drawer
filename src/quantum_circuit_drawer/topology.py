"""Public topology inputs accepted by the 3D drawing API."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal, TypeAlias, TypeGuard, cast

BuiltinTopologyName = Literal["line", "grid", "star", "star_tree", "honeycomb"]
HardwareNodeId: TypeAlias = str | int
HardwareCoordinates: TypeAlias = Mapping[HardwareNodeId, tuple[float, float]]
TopologyInput: TypeAlias = BuiltinTopologyName | "HardwareTopology"
_BUILTIN_TOPOLOGY_NAMES: tuple[BuiltinTopologyName, ...] = (
    "line",
    "grid",
    "star",
    "star_tree",
    "honeycomb",
)


@dataclass(frozen=True, slots=True)
class HardwareTopology:
    """Public custom topology for the 3D hardware view.

    ``node_ids`` defines the physical ordering that will be mapped onto the
    circuit quantum wires position-by-position. ``edges`` are treated as an
    undirected connectivity graph. ``coordinates`` can be omitted, in which
    case the layout engine derives a deterministic 2D footprint.
    """

    node_ids: tuple[HardwareNodeId, ...]
    edges: tuple[tuple[HardwareNodeId, HardwareNodeId], ...]
    coordinates: dict[HardwareNodeId, tuple[float, float]] | None = None
    name: str = "custom"

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        if not normalized_name:
            raise ValueError("topology name cannot be empty")

        normalized_node_ids = tuple(_normalize_node_id(node_id) for node_id in self.node_ids)
        if not normalized_node_ids:
            raise ValueError("HardwareTopology requires at least one node")
        if len(set(normalized_node_ids)) != len(normalized_node_ids):
            raise ValueError("HardwareTopology node_ids must be unique")

        normalized_edges = _normalize_edges(self.edges, node_ids=normalized_node_ids)
        normalized_coordinates = _normalize_coordinates(
            self.coordinates,
            node_ids=normalized_node_ids,
        )
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "node_ids", normalized_node_ids)
        object.__setattr__(self, "edges", normalized_edges)
        object.__setattr__(self, "coordinates", normalized_coordinates)

    @classmethod
    def from_coupling_map(
        cls,
        coupling_map: Iterable[tuple[HardwareNodeId, HardwareNodeId]],
        *,
        name: str = "custom",
        coordinates: HardwareCoordinates | None = None,
    ) -> HardwareTopology:
        """Build a topology from a coupling-map style edge list."""

        ordered_nodes: list[HardwareNodeId] = []
        raw_edges: list[tuple[HardwareNodeId, HardwareNodeId]] = []
        for first, second in coupling_map:
            first_node = _normalize_node_id(first)
            second_node = _normalize_node_id(second)
            ordered_nodes.extend(
                node_id for node_id in (first_node, second_node) if node_id not in ordered_nodes
            )
            raw_edges.append((first_node, second_node))
        return cls(
            node_ids=tuple(ordered_nodes),
            edges=_normalize_edges(raw_edges, node_ids=tuple(ordered_nodes)),
            coordinates=_normalize_coordinates(coordinates, node_ids=tuple(ordered_nodes)),
            name=name,
        )

    @classmethod
    def from_graph(
        cls,
        graph: Mapping[HardwareNodeId, Iterable[HardwareNodeId]]
        | Iterable[tuple[HardwareNodeId, HardwareNodeId]],
        *,
        name: str = "custom",
        coordinates: HardwareCoordinates | None = None,
    ) -> HardwareTopology:
        """Build a topology from a Python adjacency mapping or edge list."""

        ordered_nodes: list[HardwareNodeId] = []
        raw_edges: list[tuple[HardwareNodeId, HardwareNodeId]] = []

        if isinstance(graph, Mapping):
            adjacency_map = cast(Mapping[HardwareNodeId, Iterable[HardwareNodeId]], graph)
            for node_id, neighbors in adjacency_map.items():
                normalized_node = _normalize_node_id(node_id)
                if normalized_node not in ordered_nodes:
                    ordered_nodes.append(normalized_node)
                for neighbor in neighbors:
                    normalized_neighbor = _normalize_node_id(neighbor)
                    if normalized_neighbor not in ordered_nodes:
                        ordered_nodes.append(normalized_neighbor)
                    raw_edges.append((normalized_node, normalized_neighbor))
        else:
            for first, second in graph:
                first_node = _normalize_node_id(first)
                second_node = _normalize_node_id(second)
                ordered_nodes.extend(
                    node_id for node_id in (first_node, second_node) if node_id not in ordered_nodes
                )
                raw_edges.append((first_node, second_node))

        return cls(
            node_ids=tuple(ordered_nodes),
            edges=_normalize_edges(raw_edges, node_ids=tuple(ordered_nodes)),
            coordinates=_normalize_coordinates(coordinates, node_ids=tuple(ordered_nodes)),
            name=name,
        )


def builtin_topology_names() -> tuple[BuiltinTopologyName, ...]:
    """Return the built-in topology names in stable display order."""

    return _BUILTIN_TOPOLOGY_NAMES


def is_builtin_topology(value: object) -> TypeGuard[BuiltinTopologyName]:
    """Return whether a value is one of the built-in topology names."""

    return isinstance(value, str) and value in _BUILTIN_TOPOLOGY_NAMES


def is_custom_topology(value: object) -> TypeGuard[HardwareTopology]:
    """Return whether a value is a public custom hardware topology."""

    return isinstance(value, HardwareTopology)


def normalize_topology_input(value: object) -> TopologyInput:
    """Validate a public topology choice and return its typed form."""

    if is_builtin_topology(value):
        return value
    if is_custom_topology(value):
        return value
    choices = ", ".join(sorted(_BUILTIN_TOPOLOGY_NAMES))
    raise ValueError(f"topology must be one of: {choices}, or a HardwareTopology instance")


def topology_display_name(value: TopologyInput) -> str:
    """Return a user-facing name for built-in and custom topologies."""

    if is_builtin_topology(value):
        return value
    if is_custom_topology(value):
        return value.name
    raise TypeError(f"unsupported topology value {value!r}")


def _normalize_node_id(value: HardwareNodeId) -> HardwareNodeId:
    if isinstance(value, bool) or not isinstance(value, int | str):
        raise ValueError("HardwareTopology node ids must be strings or integers")
    if isinstance(value, str) and not value.strip():
        raise ValueError("HardwareTopology node ids cannot be empty")
    return value.strip() if isinstance(value, str) else value


def _normalize_edges(
    values: Iterable[tuple[HardwareNodeId, HardwareNodeId]],
    *,
    node_ids: tuple[HardwareNodeId, ...],
) -> tuple[tuple[HardwareNodeId, HardwareNodeId], ...]:
    known_node_ids = set(node_ids)
    node_positions = {node_id: index for index, node_id in enumerate(node_ids)}
    edges: list[tuple[HardwareNodeId, HardwareNodeId]] = []
    seen_edges: set[tuple[HardwareNodeId, HardwareNodeId]] = set()
    for first, second in values:
        first_node = _normalize_node_id(first)
        second_node = _normalize_node_id(second)
        if first_node not in known_node_ids or second_node not in known_node_ids:
            raise ValueError("HardwareTopology edges must reference declared node_ids")
        if first_node == second_node:
            raise ValueError("HardwareTopology edges cannot connect a node to itself")
        ordered_edge = (
            (first_node, second_node)
            if node_positions[first_node] <= node_positions[second_node]
            else (second_node, first_node)
        )
        if ordered_edge in seen_edges:
            continue
        seen_edges.add(ordered_edge)
        edges.append(ordered_edge)
    return tuple(edges)


def _normalize_coordinates(
    values: HardwareCoordinates | dict[HardwareNodeId, tuple[float, float]] | None,
    *,
    node_ids: tuple[HardwareNodeId, ...],
) -> dict[HardwareNodeId, tuple[float, float]] | None:
    if values is None:
        return None

    known_node_ids = set(node_ids)
    normalized_coordinates: dict[HardwareNodeId, tuple[float, float]] = {}
    for node_id, coordinate in values.items():
        normalized_node = _normalize_node_id(node_id)
        if normalized_node not in known_node_ids:
            raise ValueError("HardwareTopology coordinates contain unknown node ids")
        if not isinstance(coordinate, tuple | list) or len(coordinate) != 2:
            raise ValueError("HardwareTopology coordinates must be 2-item pairs")
        x_value, y_value = coordinate
        if isinstance(x_value, bool) or not isinstance(x_value, int | float):
            raise ValueError("HardwareTopology coordinates must be numeric")
        if isinstance(y_value, bool) or not isinstance(y_value, int | float):
            raise ValueError("HardwareTopology coordinates must be numeric")
        normalized_coordinates[normalized_node] = (float(x_value), float(y_value))

    missing_node_ids = [node_id for node_id in node_ids if node_id not in normalized_coordinates]
    if missing_node_ids:
        raise ValueError("HardwareTopology coordinates must be provided for every node")
    return normalized_coordinates
