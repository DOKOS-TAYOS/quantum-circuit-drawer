"""Topology-aware hover helpers shared by the 2D and 3D scene builders."""

from __future__ import annotations

from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR
from .topology_3d import Topology3D


def topology_hover_details(
    operation: OperationIR | MeasurementIR,
    topology: Topology3D | None,
) -> tuple[str, ...]:
    """Return topology-specific hover details for one operation."""

    required_swaps = required_round_trip_swaps(operation, topology)
    if required_swaps is None:
        return ()
    return (f"required SWAPs (round trip): {required_swaps}",)


def required_round_trip_swaps(
    operation: OperationIR | MeasurementIR,
    topology: Topology3D | None,
) -> int | None:
    """Return the round-trip SWAP count implied by a topology for one operation."""

    if topology is None:
        return None

    quantum_wire_ids = tuple(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
    if len(quantum_wire_ids) <= 1:
        return None
    if any(wire_id not in topology.positions for wire_id in quantum_wire_ids):
        return None

    best_intermediate_qubit_count: int | None = None
    for anchor_wire_id in quantum_wire_ids:
        intermediate_qubit_count = 0
        for wire_id in quantum_wire_ids:
            if wire_id == anchor_wire_id:
                continue
            try:
                path = topology.shortest_path(anchor_wire_id, wire_id)
            except ValueError:
                return None
            intermediate_qubit_count += max(0, len(path) - 2)
        if (
            best_intermediate_qubit_count is None
            or intermediate_qubit_count < best_intermediate_qubit_count
        ):
            best_intermediate_qubit_count = intermediate_qubit_count

    if best_intermediate_qubit_count is None:
        return None
    return best_intermediate_qubit_count * 2
