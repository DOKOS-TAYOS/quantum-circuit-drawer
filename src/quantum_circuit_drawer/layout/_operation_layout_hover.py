"""Hover and cache helpers for operation layout scene building."""

from __future__ import annotations

from collections.abc import Hashable
from typing import TYPE_CHECKING

from ..ir.measurements import MeasurementIR
from ..ir.operations import (
    CanonicalGateFamily,
    OperationIR,
    OperationKind,
    binary_control_states,
    resolved_control_values,
)
from ..ir.wires import WireIR
from ..utils.formatting import format_gate_name
from ._topology_hover import topology_hover_details
from .scene import SceneHoverData

if TYPE_CHECKING:
    from ._operation_layout import _OperationSceneBuilder
    from .topology_3d import Topology3D


def build_hover_data(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    name: str,
    gate_x: float,
    gate_y: float,
    gate_width: float,
    gate_height: float,
) -> SceneHoverData:
    matrix, matrix_dimension = hover_matrix_and_dimension(builder, operation)
    operation_id = operation.metadata.get("semantic_operation_id")
    return build_scene_hover_data(
        operation=operation,
        wire_map=builder.wire_map,
        name=name,
        key=(
            str(operation_id)
            if isinstance(operation_id, str) and operation_id
            else f"op-{column}-{id(operation)}"
        ),
        details=hover_details(
            wire_map=builder.wire_map,
            operation=operation,
            topology=builder.hover_topology,
        ),
        matrix=matrix,
        matrix_dimension=matrix_dimension,
        gate_x=gate_x,
        gate_y=gate_y,
        gate_width=gate_width,
        gate_height=gate_height,
    )


def build_scene_hover_data(
    *,
    operation: OperationIR | MeasurementIR,
    wire_map: dict[str, WireIR],
    name: str,
    key: str,
    details: tuple[str, ...],
    matrix: object | None,
    matrix_dimension: int | None,
    gate_x: float,
    gate_y: float,
    gate_width: float,
    gate_height: float,
) -> SceneHoverData:
    quantum_wire_ids = tuple(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
    other_wire_ids = [
        wire_id
        for condition in operation.classical_conditions
        for wire_id in condition.wire_ids
        if wire_id not in quantum_wire_ids
    ]
    if isinstance(operation, MeasurementIR) and operation.classical_target is not None:
        other_wire_ids.append(operation.classical_target)
    unique_other_wire_ids = tuple(dict.fromkeys(other_wire_ids))
    qubit_labels = tuple(
        (wire_map[wire_id].label or wire_map[wire_id].id) if wire_id in wire_map else wire_id
        for wire_id in quantum_wire_ids
    )
    measurement_bit_label = (
        str(operation.metadata.get("classical_bit_label"))
        if isinstance(operation, MeasurementIR)
        and operation.classical_target is not None
        and operation.metadata.get("classical_bit_label") is not None
        else None
    )
    other_wire_labels = tuple(
        measurement_bit_label
        if measurement_bit_label is not None
        and isinstance(operation, MeasurementIR)
        and operation.classical_target == wire_id
        else (wire_map[wire_id].label or wire_map[wire_id].id)
        if wire_id in wire_map
        else wire_id
        for wire_id in unique_other_wire_ids
    )
    return SceneHoverData(
        key=key,
        name=name,
        qubit_labels=qubit_labels,
        other_wire_labels=other_wire_labels,
        details=details,
        matrix=matrix,
        matrix_dimension=matrix_dimension,
        gate_x=gate_x,
        gate_y=gate_y,
        gate_width=gate_width,
        gate_height=gate_height,
    )


def hover_matrix_and_dimension(
    builder: _OperationSceneBuilder,
    operation: OperationIR,
) -> tuple[object | None, int | None]:
    cache_key = hover_matrix_cache_key(builder, operation)
    cached_matrix_data = builder.hover_matrix_cache.get(cache_key)
    if cached_matrix_data is not None:
        return cached_matrix_data

    matrix_data = (
        builder.resolved_operation_matrix_fn(operation),
        builder.operation_matrix_dimension_fn(operation),
    )
    builder.hover_matrix_cache[cache_key] = matrix_data
    return matrix_data


def hover_matrix_cache_key(
    builder: _OperationSceneBuilder,
    operation: OperationIR,
) -> tuple[object, ...]:
    explicit_matrix = operation.metadata.get("matrix")
    explicit_matrix_key = id(explicit_matrix) if explicit_matrix is not None else None
    return (
        operation.kind,
        operation.canonical_family,
        operation.name,
        len(operation.control_wires),
        len(operation.target_wires),
        tuple(tuple(int(value) for value in entry) for entry in operation.control_values),
        tuple(cache_token(builder, parameter) for parameter in operation.parameters),
        explicit_matrix_key,
    )


def cache_token(builder: _OperationSceneBuilder, value: object) -> object:
    del builder
    return value if isinstance(value, Hashable) else repr(value)


def maybe_hover_data(
    builder: _OperationSceneBuilder,
    *,
    operation: OperationIR,
    column: int,
    name: str,
    gate_x: float,
    gate_y: float,
    gate_width: float,
    gate_height: float,
) -> SceneHoverData | None:
    if not builder.hover_enabled:
        return None
    return build_hover_data(
        builder,
        operation=operation,
        column=column,
        name=name,
        gate_x=gate_x,
        gate_y=gate_y,
        gate_width=gate_width,
        gate_height=gate_height,
    )


def hover_name(
    operation: OperationIR | MeasurementIR,
    display_name: str,
) -> str:
    if operation.kind is not OperationKind.CONTROLLED_GATE:
        return display_name
    if operation.label is not None and operation.label != operation.name:
        return format_gate_name(operation.label)

    simple_binary_states = binary_control_states(operation)
    controls_are_closed = simple_binary_states is not None and all(
        state == 1 for state in simple_binary_states
    )
    if not controls_are_closed:
        return f"controlled {display_name}"

    control_count = len(operation.control_wires)
    if control_count == 1:
        if operation.canonical_family is CanonicalGateFamily.X:
            return "CNOT"
        if operation.canonical_family is CanonicalGateFamily.Z:
            return "CZ"
        return f"C{display_name}"
    if control_count == 2 and operation.canonical_family is CanonicalGateFamily.X:
        return "TOFFOLI"
    return f"{'C' * control_count}{display_name}"


def hover_details(
    *,
    wire_map: dict[str, WireIR],
    operation: OperationIR | MeasurementIR,
    topology: Topology3D | None,
) -> tuple[str, ...]:
    raw_details = operation.metadata.get("hover_details", ())
    details = (
        tuple(str(detail) for detail in raw_details if str(detail))
        if isinstance(raw_details, tuple | list)
        else ()
    )
    return (
        *details,
        *_control_hover_details(wire_map=wire_map, operation=operation),
        *topology_hover_details(operation, topology),
    )


def _control_hover_details(
    *,
    wire_map: dict[str, WireIR],
    operation: OperationIR | MeasurementIR,
) -> tuple[str, ...]:
    if operation.kind is not OperationKind.CONTROLLED_GATE or not operation.control_wires:
        return ()

    simple_binary_states = binary_control_states(operation)
    if simple_binary_states is not None:
        return (
            "control states: "
            + ", ".join(
                f"{_wire_label(wire_map, wire_id)}={state}"
                for wire_id, state in zip(
                    operation.control_wires,
                    simple_binary_states,
                    strict=True,
                )
            ),
        )

    return (
        "control values: "
        + ", ".join(
            f"{_wire_label(wire_map, wire_id)} in {{{','.join(str(value) for value in values)}}}"
            for wire_id, values in zip(
                operation.control_wires,
                resolved_control_values(operation),
                strict=True,
            )
        ),
    )


def _wire_label(wire_map: dict[str, WireIR], wire_id: str) -> str:
    wire = wire_map.get(wire_id)
    if wire is None:
        return wire_id
    return wire.label or wire.id
