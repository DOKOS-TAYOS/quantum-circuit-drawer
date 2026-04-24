"""Public topology inputs accepted by the 3D drawing API."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal, TypeAlias, TypeGuard, cast

BuiltinTopologyName = Literal["line", "grid", "star", "star_tree", "honeycomb"]
TopologyQubitMode = Literal["used", "all"]
TopologyResizeMode = Literal["error", "fit"]
HardwareNodeId: TypeAlias = str | int
HardwareCoordinates: TypeAlias = Mapping[HardwareNodeId, tuple[float, float]]
BridgeEdges: TypeAlias = tuple[tuple[HardwareNodeId, HardwareNodeId], ...]
TopologyInput: TypeAlias = (
    BuiltinTopologyName
    | "HardwareTopology"
    | "FunctionalTopology"
    | "PeriodicTopology1D"
    | "PeriodicTopology2D"
)
_BUILTIN_TOPOLOGY_NAMES: tuple[BuiltinTopologyName, ...] = (
    "line",
    "grid",
    "star",
    "star_tree",
    "honeycomb",
)
_TOPOLOGY_QUBIT_MODES: tuple[TopologyQubitMode, ...] = ("used", "all")
_TOPOLOGY_RESIZE_MODES: tuple[TopologyResizeMode, ...] = ("error", "fit")
_HEAVY_HEX_ROW_HEIGHT = math.sqrt(3.0) / 2.0
_HEAVY_HEX_BALANCE_LIMIT = 1.55
_HEAVY_HEX_SEARCH_SCALE = 4
_HEAVY_HEX_VISUAL_ROTATION_RADIANS = math.radians(30.0)
_HEAVY_HEX_SEED_CELL: tuple[tuple[int, int], ...] = (
    (0, 0),
    (0, 1),
    (-1, 1),
    (-1, 0),
    (-1, -1),
    (0, -1),
)


@dataclass(frozen=True, slots=True)
class HardwareTopology:
    """Public static topology for the 3D hardware view.

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
        normalized_name = _normalize_topology_name(self.name)
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


@dataclass(frozen=True, slots=True)
class FunctionalTopology:
    """Topology generated from a qubit-count function."""

    builder: Callable[[int], HardwareTopology]
    qubit_count: int | None = None
    name: str = "functional"

    def __post_init__(self) -> None:
        if not callable(self.builder):
            raise TypeError("FunctionalTopology builder must be callable")
        if self.qubit_count is not None:
            _validate_positive_qubit_count(self.qubit_count)
        object.__setattr__(self, "name", _normalize_topology_name(self.name))


@dataclass(frozen=True, slots=True)
class PeriodicTopology1D:
    """Topology built from an initial cell, repeated cell, and final cell."""

    initial_cell: HardwareTopology
    periodic_cell: HardwareTopology
    final_cell: HardwareTopology
    bridge_edges: BridgeEdges = ()
    repeat_count: int = 1
    name: str = "periodic_1d"

    def __post_init__(self) -> None:
        _validate_topology_cell("initial_cell", self.initial_cell)
        _validate_topology_cell("periodic_cell", self.periodic_cell)
        _validate_topology_cell("final_cell", self.final_cell)
        if isinstance(self.repeat_count, bool) or self.repeat_count < 0:
            raise ValueError("PeriodicTopology1D repeat_count must be a non-negative integer")
        object.__setattr__(self, "name", _normalize_topology_name(self.name))
        object.__setattr__(self, "bridge_edges", _normalize_bridge_edges(self.bridge_edges))


@dataclass(frozen=True, slots=True)
class PeriodicTopology2D:
    """Topology built from corner, edge, and center cells repeated in a 2D patch."""

    top_left_cell: HardwareTopology
    top_edge_cell: HardwareTopology
    top_right_cell: HardwareTopology
    left_edge_cell: HardwareTopology
    center_cell: HardwareTopology
    right_edge_cell: HardwareTopology
    bottom_left_cell: HardwareTopology
    bottom_edge_cell: HardwareTopology
    bottom_right_cell: HardwareTopology
    horizontal_bridge_edges: BridgeEdges = ()
    vertical_bridge_edges: BridgeEdges = ()
    rows: int = 1
    columns: int = 1
    name: str = "periodic_2d"

    def __post_init__(self) -> None:
        for field_name in (
            "top_left_cell",
            "top_edge_cell",
            "top_right_cell",
            "left_edge_cell",
            "center_cell",
            "right_edge_cell",
            "bottom_left_cell",
            "bottom_edge_cell",
            "bottom_right_cell",
        ):
            _validate_topology_cell(field_name, getattr(self, field_name))
        if isinstance(self.rows, bool) or self.rows < 1:
            raise ValueError("PeriodicTopology2D rows must be a positive integer")
        if isinstance(self.columns, bool) or self.columns < 1:
            raise ValueError("PeriodicTopology2D columns must be a positive integer")
        object.__setattr__(self, "name", _normalize_topology_name(self.name))
        object.__setattr__(
            self,
            "horizontal_bridge_edges",
            _normalize_bridge_edges(self.horizontal_bridge_edges),
        )
        object.__setattr__(
            self,
            "vertical_bridge_edges",
            _normalize_bridge_edges(self.vertical_bridge_edges),
        )


def builtin_topology_names() -> tuple[BuiltinTopologyName, ...]:
    """Return the built-in topology names in stable display order."""

    return _BUILTIN_TOPOLOGY_NAMES


def is_builtin_topology(value: object) -> TypeGuard[BuiltinTopologyName]:
    """Return whether a value is one of the built-in topology names."""

    return isinstance(value, str) and value in _BUILTIN_TOPOLOGY_NAMES


def is_custom_topology(value: object) -> TypeGuard[HardwareTopology]:
    """Return whether a value is a public static hardware topology."""

    return isinstance(value, HardwareTopology)


def is_functional_topology(value: object) -> TypeGuard[FunctionalTopology]:
    """Return whether a value is a public functional topology."""

    return isinstance(value, FunctionalTopology)


def is_periodic_topology(value: object) -> TypeGuard[PeriodicTopology1D | PeriodicTopology2D]:
    """Return whether a value is a public periodic topology."""

    return isinstance(value, PeriodicTopology1D | PeriodicTopology2D)


def normalize_topology_input(value: object) -> TopologyInput:
    """Validate a public topology choice and return its typed form."""

    if is_builtin_topology(value):
        return value
    if isinstance(
        value, HardwareTopology | FunctionalTopology | PeriodicTopology1D | PeriodicTopology2D
    ):
        return value
    choices = ", ".join(sorted(_BUILTIN_TOPOLOGY_NAMES))
    raise ValueError(
        "topology must be one of: "
        f"{choices}, or a HardwareTopology, FunctionalTopology, "
        "PeriodicTopology1D, or PeriodicTopology2D instance"
    )


def normalize_topology_qubits(value: object) -> TopologyQubitMode:
    """Validate how many topology qubits should be rendered."""

    if isinstance(value, str) and value in _TOPOLOGY_QUBIT_MODES:
        return cast(TopologyQubitMode, value)
    choices = ", ".join(_TOPOLOGY_QUBIT_MODES)
    raise ValueError(f"topology_qubits must be one of: {choices}")


def normalize_topology_resize(value: object) -> TopologyResizeMode:
    """Validate how non-static topologies should handle undersized layouts."""

    if isinstance(value, str) and value in _TOPOLOGY_RESIZE_MODES:
        return cast(TopologyResizeMode, value)
    choices = ", ".join(_TOPOLOGY_RESIZE_MODES)
    raise ValueError(f"topology_resize must be one of: {choices}")


def topology_display_name(value: TopologyInput) -> str:
    """Return a user-facing name for built-in and custom topologies."""

    if is_builtin_topology(value):
        return value
    if isinstance(
        value, HardwareTopology | FunctionalTopology | PeriodicTopology1D | PeriodicTopology2D
    ):
        return value.name
    raise TypeError(f"unsupported topology value {value!r}")


def line_topology(qubit_count: int) -> HardwareTopology:
    """Build a linear topology for the requested number of qubits."""

    _validate_positive_qubit_count(qubit_count)
    node_ids = tuple(range(qubit_count))
    return HardwareTopology(
        node_ids=node_ids,
        edges=tuple((index, index + 1) for index in range(qubit_count - 1)),
        coordinates={index: (float(index), 0.0) for index in node_ids},
        name="line",
    )


def grid_topology(qubit_count: int) -> HardwareTopology:
    """Build a near-square ragged grid topology for the requested qubits."""

    _validate_positive_qubit_count(qubit_count)
    columns = _compact_grid_column_count(qubit_count)
    node_ids = tuple(range(qubit_count))
    row_starts = tuple(range(0, qubit_count, columns))
    row_widths = tuple(min(columns, qubit_count - row_start) for row_start in row_starts)
    row_offsets = tuple(
        _compact_grid_row_offset(columns=columns, row_width=row_width) for row_width in row_widths
    )
    coordinates: dict[HardwareNodeId, tuple[float, float]] = {}
    edges: list[tuple[HardwareNodeId, HardwareNodeId]] = []
    for row, row_start in enumerate(row_starts):
        row_width = row_widths[row]
        row_offset = row_offsets[row]
        for column in range(row_width):
            index = row_start + column
            coordinates[index] = (row_offset + float(column), float(-row))
            if column > 0:
                edges.append((index - 1, index))
            if row > 0:
                previous_row_start = row_starts[row - 1]
                previous_row_width = row_widths[row - 1]
                previous_row_offset = row_offsets[row - 1]
                above_column = min(
                    previous_row_width - 1,
                    max(0, int(round(coordinates[index][0] - previous_row_offset))),
                )
                edges.append((previous_row_start + above_column, index))
    return HardwareTopology(
        node_ids=node_ids,
        edges=tuple(edges),
        coordinates=coordinates,
        name="grid",
    )


def _compact_grid_column_count(qubit_count: int) -> int:
    square_side = math.isqrt(qubit_count)
    remainder = qubit_count - (square_side * square_side)
    if remainder == 0:
        return square_side
    if remainder <= math.ceil(square_side / 2.0):
        return square_side
    return square_side + 1


def _compact_grid_row_offset(*, columns: int, row_width: int) -> float:
    if row_width == columns:
        return 0.0
    return float(columns - row_width) / 2.0


def star_topology(qubit_count: int) -> HardwareTopology:
    """Build a star topology, allowing a single center-only qubit."""

    _validate_positive_qubit_count(qubit_count)
    node_ids = tuple(range(qubit_count))
    if qubit_count == 1:
        return HardwareTopology(
            node_ids=node_ids,
            edges=(),
            coordinates={0: (0.0, 0.0)},
            name="star",
        )

    leaf_count = qubit_count - 1
    coordinates: dict[HardwareNodeId, tuple[float, float]] = {0: (0.0, 0.0)}
    for leaf_index in range(1, qubit_count):
        angle = (2.0 * math.pi * (leaf_index - 1)) / leaf_count
        coordinates[leaf_index] = (math.cos(angle) * 2.1, math.sin(angle) * 2.1)
    return HardwareTopology(
        node_ids=node_ids,
        edges=tuple((0, leaf_index) for leaf_index in range(1, qubit_count)),
        coordinates=coordinates,
        name="star",
    )


def star_tree_topology(qubit_count: int) -> HardwareTopology:
    """Build a breadth-first three-branch star-tree topology."""

    _validate_positive_qubit_count(qubit_count)
    node_ids = tuple(range(qubit_count))
    coordinates: dict[HardwareNodeId, tuple[float, float]] = {0: (0.0, 0.0)}
    edges: list[tuple[HardwareNodeId, HardwareNodeId]] = []
    if qubit_count == 1:
        return HardwareTopology(
            node_ids=node_ids, edges=(), coordinates=coordinates, name="star_tree"
        )

    frontier: list[tuple[int, float, int]] = [
        (0, math.pi / 2.0, 1),
        (0, 7.0 * math.pi / 6.0, 1),
        (0, 11.0 * math.pi / 6.0, 1),
    ]
    next_node = 1
    while frontier and next_node < qubit_count:
        parent_node, angle, level = frontier.pop(0)
        radius = level * 1.8
        coordinates[next_node] = (math.cos(angle) * radius, math.sin(angle) * radius)
        edges.append((parent_node, next_node))
        angle_spread = math.pi / max(4.0, 4.0 * level)
        frontier.append((next_node, angle - angle_spread, level + 1))
        frontier.append((next_node, angle + angle_spread, level + 1))
        next_node += 1
    return HardwareTopology(
        node_ids=node_ids,
        edges=tuple(edges),
        coordinates=coordinates,
        name="star_tree",
    )


def honeycomb_topology(qubit_count: int) -> HardwareTopology:
    """Build a compact deterministic IBM-inspired hexagonal chip patch."""

    _validate_positive_qubit_count(qubit_count)
    raw_coordinates, edges = _compact_heavy_hex_patch(qubit_count)
    return HardwareTopology(
        node_ids=tuple(range(qubit_count)),
        edges=tuple(edges),
        coordinates=_centered_coordinates(_rotate_coordinates(raw_coordinates)),
        name="honeycomb",
    )


_HeavyHexKey: TypeAlias = tuple[int, int]


def _compact_heavy_hex_patch(
    qubit_count: int,
) -> tuple[dict[int, tuple[float, float]], tuple[tuple[int, int], ...]]:
    search_limit = _heavy_hex_search_limit(qubit_count)
    while True:
        lattice = _heavy_hex_lattice(search_limit)
        selected_keys = _select_compact_heavy_hex_keys(lattice, qubit_count)
        if len(selected_keys) == qubit_count:
            node_id_by_key = {key: node_id for node_id, key in enumerate(selected_keys)}
            coordinates = {node_id_by_key[key]: lattice[key] for key in selected_keys}
            edges = _heavy_hex_edges_for_selected_keys(
                selected_keys,
                node_id_by_key=node_id_by_key,
            )
            return coordinates, edges
        search_limit *= 2


def _heavy_hex_search_limit(qubit_count: int) -> int:
    return max(4, math.ceil(math.sqrt(float(qubit_count))) * _HEAVY_HEX_SEARCH_SCALE)


def _heavy_hex_lattice(search_limit: int) -> dict[_HeavyHexKey, tuple[float, float]]:
    lattice: dict[_HeavyHexKey, tuple[float, float]] = {}
    for row in range(-search_limit, search_limit + 1):
        y_position = float(row) * _HEAVY_HEX_ROW_HEIGHT
        horizontal_shift = 0.5 if row % 2 else 0.0
        for column in range(-search_limit, search_limit + 1):
            lattice[(row, column)] = (float(column) + horizontal_shift, y_position)
    return lattice


def _select_compact_heavy_hex_keys(
    lattice: Mapping[_HeavyHexKey, tuple[float, float]],
    qubit_count: int,
) -> tuple[_HeavyHexKey, ...]:
    selected = [key for key in _HEAVY_HEX_SEED_CELL[:qubit_count] if key in lattice]
    if not selected:
        root = min(lattice, key=lambda key: _heavy_hex_key_priority(key, lattice[key]))
        selected = [root]
    visited: set[_HeavyHexKey] = set(selected)
    frontier: set[_HeavyHexKey] = set()
    for key in selected:
        _add_heavy_hex_neighbors(key, lattice=lattice, visited=visited, frontier=frontier)

    while frontier and len(selected) < qubit_count:
        key = min(
            frontier,
            key=lambda candidate: _heavy_hex_expansion_priority(
                candidate,
                selected_keys=selected,
                lattice=lattice,
            ),
        )
        frontier.remove(key)
        visited.add(key)
        selected.append(key)
        _add_heavy_hex_neighbors(key, lattice=lattice, visited=visited, frontier=frontier)
    return tuple(selected)


def _add_heavy_hex_neighbors(
    key: _HeavyHexKey,
    *,
    lattice: Mapping[_HeavyHexKey, tuple[float, float]],
    visited: set[_HeavyHexKey],
    frontier: set[_HeavyHexKey],
) -> None:
    for neighbor in _heavy_hex_neighbor_keys(key):
        if neighbor in visited or neighbor not in lattice:
            continue
        frontier.add(neighbor)


def _heavy_hex_expansion_priority(
    key: _HeavyHexKey,
    *,
    selected_keys: Sequence[_HeavyHexKey],
    lattice: Mapping[_HeavyHexKey, tuple[float, float]],
) -> tuple[float, float, float, int, int]:
    positions = [lattice[selected_key] for selected_key in selected_keys]
    positions.append(lattice[key])
    x_values = [position[0] for position in positions]
    y_values = [position[1] for position in positions]
    width = max(x_values) - min(x_values)
    height = max(y_values) - min(y_values)
    effective_width = max(width, 1.0)
    effective_height = max(height, _HEAVY_HEX_ROW_HEIGHT)
    area = effective_width * effective_height
    aspect = effective_width / effective_height
    balance_ratio = max(aspect, 1.0 / aspect)
    aspect_penalty = 1.0 + max(0.0, balance_ratio - _HEAVY_HEX_BALANCE_LIMIT) ** 2
    distance, _center_bias, row_bias, x_bias = _heavy_hex_key_priority(key, lattice[key])
    return (
        area * aspect_penalty,
        max(effective_width, effective_height),
        distance,
        row_bias,
        x_bias,
    )


def _heavy_hex_key_priority(
    key: _HeavyHexKey,
    position: tuple[float, float],
) -> tuple[float, float, int, int]:
    row, x_position = key
    x_value, y_value = position
    return (
        (x_value * x_value) + (y_value * y_value),
        abs(y_value) + (abs(x_value) * 0.25),
        abs(row),
        x_position,
    )


def _heavy_hex_edges_for_selected_keys(
    selected_keys: tuple[_HeavyHexKey, ...],
    *,
    node_id_by_key: Mapping[_HeavyHexKey, int],
) -> tuple[tuple[int, int], ...]:
    selected_set = set(selected_keys)
    edges: list[tuple[int, int]] = []
    seen_edges: set[tuple[int, int]] = set()
    for key in selected_keys:
        first_node = node_id_by_key[key]
        for neighbor in _heavy_hex_neighbor_keys(key):
            if neighbor not in selected_set:
                continue
            second_node = node_id_by_key[neighbor]
            edge = (
                (first_node, second_node) if first_node < second_node else (second_node, first_node)
            )
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            edges.append(edge)
    return tuple(edges)


def _heavy_hex_neighbor_keys(key: _HeavyHexKey) -> tuple[_HeavyHexKey, ...]:
    row, column = key
    neighbors = [(row, column - 1), (row, column + 1)]
    diagonal_row = row + 1 if (row + column) % 2 == 0 else row - 1
    neighbors.append((diagonal_row, column))
    return tuple(neighbors)


def materialize_topology(
    topology: TopologyInput,
    *,
    qubit_count: int,
    topology_resize: TopologyResizeMode,
) -> HardwareTopology:
    """Return a concrete hardware topology for a circuit qubit count."""

    _validate_positive_qubit_count(qubit_count)
    resize = normalize_topology_resize(topology_resize)
    if is_builtin_topology(topology):
        return _BUILTIN_TOPOLOGY_BUILDERS[topology](qubit_count)
    if isinstance(topology, HardwareTopology):
        _raise_if_static_topology_too_small(topology, qubit_count)
        return topology
    if isinstance(topology, FunctionalTopology):
        resolved_count = topology.qubit_count or qubit_count
        if resolved_count < qubit_count:
            if resize == "fit":
                resolved_count = qubit_count
            else:
                _raise_if_topology_too_small(topology.name, resolved_count, qubit_count)
        built_topology = topology.builder(resolved_count)
        if not isinstance(built_topology, HardwareTopology):
            raise TypeError("FunctionalTopology builder must return a HardwareTopology")
        if len(built_topology.node_ids) < qubit_count:
            _raise_if_topology_too_small(topology.name, len(built_topology.node_ids), qubit_count)
        return replace(built_topology, name=topology.name)
    if isinstance(topology, PeriodicTopology1D):
        repeat_count = topology.repeat_count
        if _periodic_1d_node_count(topology, repeat_count=repeat_count) < qubit_count:
            if resize == "fit":
                repeat_count = _periodic_1d_repeat_count_for_required(topology, qubit_count)
            else:
                _raise_if_topology_too_small(
                    topology.name,
                    _periodic_1d_node_count(topology, repeat_count=repeat_count),
                    qubit_count,
                )
        return _materialize_periodic_1d(topology, repeat_count=repeat_count)
    if isinstance(topology, PeriodicTopology2D):
        rows = topology.rows
        columns = topology.columns
        if _periodic_2d_node_count(topology, rows=rows, columns=columns) < qubit_count:
            if resize == "fit":
                rows, columns = _periodic_2d_shape_for_required(topology, qubit_count)
            else:
                _raise_if_topology_too_small(
                    topology.name,
                    _periodic_2d_node_count(topology, rows=rows, columns=columns),
                    qubit_count,
                )
        return _materialize_periodic_2d(topology, rows=rows, columns=columns)
    raise ValueError(f"unknown topology {topology!r}")


def _materialize_periodic_1d(
    topology: PeriodicTopology1D,
    *,
    repeat_count: int,
) -> HardwareTopology:
    cells = [
        ("initial_0", topology.initial_cell),
        *[(f"periodic_{index}", topology.periodic_cell) for index in range(repeat_count)],
        ("final_0", topology.final_cell),
    ]
    step_x = _cell_step_x(cell for _, cell in cells)
    nodes: list[HardwareNodeId] = []
    edges: list[tuple[HardwareNodeId, HardwareNodeId]] = []
    coordinates: dict[HardwareNodeId, tuple[float, float]] = {}
    namespaced_node_ids_by_cell: list[dict[HardwareNodeId, HardwareNodeId]] = []

    for cell_index, (cell_prefix, cell) in enumerate(cells):
        mapping = _append_cell(
            nodes=nodes,
            edges=edges,
            coordinates=coordinates,
            cell=cell,
            cell_prefix=cell_prefix,
            offset_x=float(cell_index) * step_x,
            offset_y=0.0,
        )
        namespaced_node_ids_by_cell.append(mapping)

    for index, (left, right) in enumerate(zip(cells, cells[1:], strict=False)):
        left_mapping = namespaced_node_ids_by_cell[index]
        right_mapping = namespaced_node_ids_by_cell[index + 1]
        _append_bridge_edges(
            edges=edges,
            bridge_edges=topology.bridge_edges,
            left_cell=left[1],
            right_cell=right[1],
            left_mapping=left_mapping,
            right_mapping=right_mapping,
        )

    return HardwareTopology(
        node_ids=tuple(nodes),
        edges=tuple(edges),
        coordinates=coordinates,
        name=topology.name,
    )


def _materialize_periodic_2d(
    topology: PeriodicTopology2D,
    *,
    rows: int,
    columns: int,
) -> HardwareTopology:
    cell_grid = [
        [
            _periodic_2d_cell_for_position(
                topology,
                row=row,
                column=column,
                rows=rows,
                columns=columns,
            )
            for column in range(columns + 2)
        ]
        for row in range(rows + 2)
    ]
    all_cells = [cell for row_cells in cell_grid for cell in row_cells]
    step_x = _cell_step_x(all_cells)
    step_y = _cell_step_y(all_cells)
    nodes: list[HardwareNodeId] = []
    edges: list[tuple[HardwareNodeId, HardwareNodeId]] = []
    coordinates: dict[HardwareNodeId, tuple[float, float]] = {}
    mappings: list[list[dict[HardwareNodeId, HardwareNodeId]]] = []

    for row, row_cells in enumerate(cell_grid):
        mapping_row: list[dict[HardwareNodeId, HardwareNodeId]] = []
        for column, cell in enumerate(row_cells):
            mapping_row.append(
                _append_cell(
                    nodes=nodes,
                    edges=edges,
                    coordinates=coordinates,
                    cell=cell,
                    cell_prefix=f"r{row}_c{column}",
                    offset_x=float(column) * step_x,
                    offset_y=float(-row) * step_y,
                )
            )
        mappings.append(mapping_row)

    for row, row_cells in enumerate(cell_grid):
        for column, (left_cell, right_cell) in enumerate(
            zip(row_cells, row_cells[1:], strict=False)
        ):
            _append_bridge_edges(
                edges=edges,
                bridge_edges=topology.horizontal_bridge_edges,
                left_cell=left_cell,
                right_cell=right_cell,
                left_mapping=mappings[row][column],
                right_mapping=mappings[row][column + 1],
            )
    for row, (upper_row, lower_row) in enumerate(zip(cell_grid, cell_grid[1:], strict=False)):
        for column, (upper_cell, lower_cell) in enumerate(zip(upper_row, lower_row, strict=False)):
            _append_bridge_edges(
                edges=edges,
                bridge_edges=topology.vertical_bridge_edges,
                left_cell=upper_cell,
                right_cell=lower_cell,
                left_mapping=mappings[row][column],
                right_mapping=mappings[row + 1][column],
            )

    return HardwareTopology(
        node_ids=tuple(nodes),
        edges=tuple(edges),
        coordinates=coordinates,
        name=topology.name,
    )


def _periodic_2d_cell_for_position(
    topology: PeriodicTopology2D,
    *,
    row: int,
    column: int,
    rows: int,
    columns: int,
) -> HardwareTopology:
    last_row = rows + 1
    last_column = columns + 1
    if row == 0 and column == 0:
        return topology.top_left_cell
    if row == 0 and column == last_column:
        return topology.top_right_cell
    if row == last_row and column == 0:
        return topology.bottom_left_cell
    if row == last_row and column == last_column:
        return topology.bottom_right_cell
    if row == 0:
        return topology.top_edge_cell
    if row == last_row:
        return topology.bottom_edge_cell
    if column == 0:
        return topology.left_edge_cell
    if column == last_column:
        return topology.right_edge_cell
    return topology.center_cell


def _periodic_1d_node_count(topology: PeriodicTopology1D, *, repeat_count: int) -> int:
    return (
        len(topology.initial_cell.node_ids)
        + (repeat_count * len(topology.periodic_cell.node_ids))
        + len(topology.final_cell.node_ids)
    )


def _periodic_1d_repeat_count_for_required(
    topology: PeriodicTopology1D,
    required_count: int,
) -> int:
    repeat_count = topology.repeat_count
    while _periodic_1d_node_count(topology, repeat_count=repeat_count) < required_count:
        repeat_count += 1
    return repeat_count


def _periodic_2d_node_count(
    topology: PeriodicTopology2D,
    *,
    rows: int,
    columns: int,
) -> int:
    corner_count = (
        len(topology.top_left_cell.node_ids)
        + len(topology.top_right_cell.node_ids)
        + len(topology.bottom_left_cell.node_ids)
        + len(topology.bottom_right_cell.node_ids)
    )
    horizontal_edge_count = columns * (
        len(topology.top_edge_cell.node_ids) + len(topology.bottom_edge_cell.node_ids)
    )
    vertical_edge_count = rows * (
        len(topology.left_edge_cell.node_ids) + len(topology.right_edge_cell.node_ids)
    )
    center_count = rows * columns * len(topology.center_cell.node_ids)
    return corner_count + horizontal_edge_count + vertical_edge_count + center_count


def _periodic_2d_shape_for_required(
    topology: PeriodicTopology2D,
    required_count: int,
) -> tuple[int, int]:
    target_aspect = (topology.rows + 2) / float(topology.columns + 2)
    limit = max(topology.rows, topology.columns, 1)
    while True:
        candidates: list[tuple[float, int, int, int]] = []
        for rows in range(topology.rows, limit + 1):
            for columns in range(topology.columns, limit + 1):
                node_count = _periodic_2d_node_count(topology, rows=rows, columns=columns)
                if node_count < required_count:
                    continue
                aspect = (rows + 2) / float(columns + 2)
                candidates.append((abs(aspect - target_aspect), node_count, rows, columns))
        if candidates:
            _, _, rows, columns = min(candidates)
            return rows, columns
        limit *= 2


def _append_cell(
    *,
    nodes: list[HardwareNodeId],
    edges: list[tuple[HardwareNodeId, HardwareNodeId]],
    coordinates: dict[HardwareNodeId, tuple[float, float]],
    cell: HardwareTopology,
    cell_prefix: str,
    offset_x: float,
    offset_y: float,
) -> dict[HardwareNodeId, HardwareNodeId]:
    cell_coordinates = _coordinates_for_cell(cell)
    mapping: dict[HardwareNodeId, HardwareNodeId] = {}
    for node_id in cell.node_ids:
        namespaced_id = f"{cell_prefix}_{_node_id_slug(node_id)}"
        mapping[node_id] = namespaced_id
        nodes.append(namespaced_id)
        x_value, y_value = cell_coordinates[node_id]
        coordinates[namespaced_id] = (x_value + offset_x, y_value + offset_y)
    for first, second in cell.edges:
        edges.append((mapping[first], mapping[second]))
    return mapping


def _append_bridge_edges(
    *,
    edges: list[tuple[HardwareNodeId, HardwareNodeId]],
    bridge_edges: BridgeEdges,
    left_cell: HardwareTopology,
    right_cell: HardwareTopology,
    left_mapping: dict[HardwareNodeId, HardwareNodeId],
    right_mapping: dict[HardwareNodeId, HardwareNodeId],
) -> None:
    left_node_ids = set(left_cell.node_ids)
    right_node_ids = set(right_cell.node_ids)
    for left_node_id, right_node_id in bridge_edges:
        if left_node_id not in left_node_ids or right_node_id not in right_node_ids:
            raise ValueError("periodic topology bridge_edges must reference adjacent cell nodes")
        edges.append((left_mapping[left_node_id], right_mapping[right_node_id]))


def _coordinates_for_cell(cell: HardwareTopology) -> dict[HardwareNodeId, tuple[float, float]]:
    if cell.coordinates is not None:
        return dict(cell.coordinates)
    return {node_id: (float(index), 0.0) for index, node_id in enumerate(cell.node_ids)}


def _cell_step_x(cells: Iterable[HardwareTopology]) -> float:
    widths = []
    for cell in cells:
        coordinates = _coordinates_for_cell(cell)
        x_values = [position[0] for position in coordinates.values()]
        widths.append(max(x_values) - min(x_values) if x_values else 0.0)
    return max(widths, default=0.0) + 1.6


def _cell_step_y(cells: Iterable[HardwareTopology]) -> float:
    heights = []
    for cell in cells:
        coordinates = _coordinates_for_cell(cell)
        y_values = [position[1] for position in coordinates.values()]
        heights.append(max(y_values) - min(y_values) if y_values else 0.0)
    return max(heights, default=0.0) + 1.6


def _raise_if_static_topology_too_small(topology: HardwareTopology, qubit_count: int) -> None:
    if len(topology.node_ids) >= qubit_count:
        return
    raise ValueError(
        f"static topology '{topology.name}' has {len(topology.node_ids)} nodes "
        f"but circuit uses {qubit_count}"
    )


def _raise_if_topology_too_small(topology_name: str, node_count: int, qubit_count: int) -> None:
    raise ValueError(
        f"topology '{topology_name}' has {node_count} nodes but circuit uses {qubit_count}"
    )


def _normalize_topology_name(value: str) -> str:
    normalized_name = str(value).strip()
    if not normalized_name:
        raise ValueError("topology name cannot be empty")
    return normalized_name


def _validate_topology_cell(name: str, value: object) -> None:
    if isinstance(value, HardwareTopology):
        return
    raise TypeError(f"{name} must be a HardwareTopology")


def _validate_positive_qubit_count(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("qubit_count must be a positive integer")


def _normalize_node_id(value: HardwareNodeId) -> HardwareNodeId:
    if isinstance(value, bool) or not isinstance(value, int | str):
        raise ValueError("HardwareTopology node ids must be strings or integers")
    if isinstance(value, str) and not value.strip():
        raise ValueError("HardwareTopology node ids cannot be empty")
    return value.strip() if isinstance(value, str) else value


def _normalize_bridge_edges(values: Iterable[tuple[HardwareNodeId, HardwareNodeId]]) -> BridgeEdges:
    return tuple(
        (_normalize_node_id(first), _normalize_node_id(second)) for first, second in values
    )


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


def _centered_coordinates(
    values: Mapping[int, tuple[float, float]],
) -> dict[HardwareNodeId, tuple[float, float]]:
    if not values:
        return {}
    mean_x = sum(position[0] for position in values.values()) / len(values)
    mean_y = sum(position[1] for position in values.values()) / len(values)
    return {
        node_id: (round(position[0] - mean_x, 6), round(position[1] - mean_y, 6))
        for node_id, position in values.items()
    }


def _rotate_coordinates(
    values: Mapping[int, tuple[float, float]],
) -> dict[int, tuple[float, float]]:
    cos_angle = math.cos(_HEAVY_HEX_VISUAL_ROTATION_RADIANS)
    sin_angle = math.sin(_HEAVY_HEX_VISUAL_ROTATION_RADIANS)
    return {
        node_id: (
            (position[0] * cos_angle) - (position[1] * sin_angle),
            (position[0] * sin_angle) + (position[1] * cos_angle),
        )
        for node_id, position in values.items()
    }


def _node_id_slug(node_id: HardwareNodeId) -> str:
    text = str(node_id).strip()
    slug = re.sub(r"[^0-9A-Za-z_]+", "_", text)
    return slug.strip("_") or "node"


_BUILTIN_TOPOLOGY_BUILDERS: dict[BuiltinTopologyName, Callable[[int], HardwareTopology]] = {
    "line": line_topology,
    "grid": grid_topology,
    "star": star_topology,
    "star_tree": star_tree_topology,
    "honeycomb": honeycomb_topology,
}


__all__ = [
    "BridgeEdges",
    "BuiltinTopologyName",
    "FunctionalTopology",
    "HardwareCoordinates",
    "HardwareNodeId",
    "HardwareTopology",
    "PeriodicTopology1D",
    "PeriodicTopology2D",
    "TopologyInput",
    "TopologyQubitMode",
    "TopologyResizeMode",
    "builtin_topology_names",
    "grid_topology",
    "honeycomb_topology",
    "is_builtin_topology",
    "is_custom_topology",
    "is_functional_topology",
    "is_periodic_topology",
    "line_topology",
    "materialize_topology",
    "normalize_topology_input",
    "normalize_topology_qubits",
    "normalize_topology_resize",
    "star_topology",
    "star_tree_topology",
    "topology_display_name",
]
