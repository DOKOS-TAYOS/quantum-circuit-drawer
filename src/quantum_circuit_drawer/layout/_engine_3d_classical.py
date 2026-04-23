"""Classical-condition connection helpers for the 3D layout engine."""

from __future__ import annotations

from ..ir.operations import OperationIR
from ._classical_conditions import iter_classical_condition_anchors
from .scene_3d import Point3D, SceneConnection3D


def append_classical_condition_connections_3d(
    *,
    operation: OperationIR,
    column: int,
    gate_center: Point3D,
    classical_wire_positions: dict[str, Point3D],
    connections: list[SceneConnection3D],
) -> None:
    """Append classical-condition connectors targeting a 3D gate center."""

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
                operation_id=_operation_id_3d(operation),
            )
        )


def _operation_id_3d(operation: OperationIR) -> str | None:
    resolved = operation.metadata.get("semantic_operation_id")
    if isinstance(resolved, str) and resolved:
        return resolved
    return None
