"""Operation-layout helpers for the 3D layout engine."""

from __future__ import annotations

from collections.abc import Sequence

from ..ir.operations import CanonicalGateFamily, OperationIR, binary_control_states
from ..style import DrawStyle
from ._engine_3d_metrics import _OperationMetrics3D
from .scene_3d import Point3D
from .topology_3d import Topology3D

_Z_STEP = 0.625
_COLUMN_DEPTH_GAP = 0.12
_GATE_SIZE = 0.72
_GATE_DEPTH = 0.72


def point_for_wire_3d(
    wire_id: str,
    quantum_wire_positions: dict[str, Point3D],
    gate_z: float,
) -> Point3D:
    """Return a point on one quantum wire at the requested depth."""

    point = quantum_wire_positions[wire_id]
    return Point3D(x=point.x, y=point.y, z=gate_z)


def nearest_anchor_wire_3d(
    *,
    control_wire_id: str,
    anchor_wire_ids: Sequence[str],
    topology: Topology3D,
) -> str:
    """Choose the nearest anchor wire for a controlled connection."""

    distances = [
        (
            len(topology.shortest_path(control_wire_id, anchor_wire_id)),
            anchor_index,
            anchor_wire_id,
        )
        for anchor_index, anchor_wire_id in enumerate(anchor_wire_ids)
    ]
    return min(distances)[2]


def connection_points_3d(
    *,
    topology: Topology3D,
    control_wire_id: str,
    target_wire_id: str,
    control_point: Point3D,
    anchor_point: Point3D,
    direct: bool,
) -> tuple[Point3D, ...]:
    """Return the direct or topology-routed connection points."""

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


def uses_canonical_controlled_x_target_3d(operation: OperationIR) -> bool:
    """Return whether the operation should render as an X target."""

    if binary_control_states(operation) is None:
        return False
    return (
        operation.canonical_family is CanonicalGateFamily.X
        and len(operation.target_wires) == 1
        and not operation.parameters
    )


def uses_canonical_controlled_z_3d(operation: OperationIR) -> bool:
    """Return whether the operation should collapse into controlled-Z markers."""

    if binary_control_states(operation) is None:
        return False
    return (
        operation.canonical_family is CanonicalGateFamily.Z
        and len(operation.target_wires) == 1
        and not operation.parameters
    )


def gate_hover_text_3d(metrics: _OperationMetrics3D) -> str:
    """Build the hover text shown for a 3D gate."""

    if metrics.subtitle:
        return f"{metrics.display_label}({metrics.subtitle})"
    return metrics.display_label


def gate_cube_size_3d(style: DrawStyle) -> float:
    """Return the gate cube size used by 3D layout."""

    return max(_GATE_SIZE, _GATE_DEPTH, style.gate_width, style.gate_height)


def column_depth_step_3d(style: DrawStyle) -> float:
    """Return the z-step used between gate columns."""

    return max(_Z_STEP, gate_cube_size_3d(style) + _COLUMN_DEPTH_GAP)


def fit_gate_text_size_3d(
    *,
    text: str,
    gate_size: float,
    default_font_size: float,
) -> float:
    """Fit a gate text block to the available cube size."""

    if not text:
        return default_font_size

    text_lines = text.split("\n")
    longest_line_length = max((len(line) for line in text_lines), default=1)
    line_count = len(text_lines)
    available_character_units = gate_size * 4.2
    width_scale = min(1.0, available_character_units / longest_line_length)
    height_scale = min(1.0, 1.7 / max(1, line_count))
    return max(3.5, default_font_size * min(width_scale, height_scale))
