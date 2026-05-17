"""Semantic circuit IR that preserves framework-native structure and provenance."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

from ..diagnostics import RenderDiagnostic
from ..typing import Metadata
from .classical_conditions import ClassicalConditionIR
from .operations import (
    CanonicalGateFamily,
    OperationKind,
    _normalize_canonical_gate_family,
    _normalize_control_values,
    _normalize_operation_kind,
    infer_canonical_gate_family,
)
from .wires import WireIR, WireKind


def _normalize_wire_ids(values: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(str(value) for value in values)
    if any(not wire_id for wire_id in normalized):
        raise ValueError("wire id cannot be empty")
    return normalized


def _normalize_parameters(values: Sequence[object]) -> tuple[object, ...]:
    return tuple(values)


def _normalize_classical_conditions(
    values: Sequence[ClassicalConditionIR],
) -> tuple[ClassicalConditionIR, ...]:
    return tuple(values)


def _normalize_texts(values: Sequence[object]) -> tuple[str, ...]:
    return tuple(str(value) for value in values if str(value))


def _metadata_wire_dependencies(metadata: Metadata) -> tuple[str, ...]:
    value = metadata.get("occupied_wire_dependencies")
    if isinstance(value, str):
        return (value,) if value else ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(wire_id) for wire_id in value if str(wire_id))


def _parameter_signature_token(value: object) -> object:
    try:
        hash(value)
    except TypeError:
        return repr(value)
    return value


def semantic_operation_id_from_location(location: Sequence[int]) -> str:
    """Return a stable operation id from semantic provenance location.

    Args:
        location: Sequence of nested indices that identify an operation inside native
            framework structure.

    Returns:
        String id such as ``"op:1.2.0"``. Empty locations return ``"op:root"``.
    """

    resolved_location = tuple(int(index) for index in location)
    if not resolved_location:
        return "op:root"
    return "op:" + ".".join(str(index) for index in resolved_location)


@dataclass(frozen=True, slots=True)
class SemanticProvenanceIR:
    """Framework-native provenance attached to one semantic operation.

    Attributes:
        framework: Source framework name, such as ``"qiskit"`` or ``"cudaq"``.
        native_name: Native operation or instruction name.
        native_kind: Native operation category.
        grouping: Semantic grouping label, for example control-flow or composite block.
        decomposition_origin: Name of the operation that produced this expanded body.
        composite_label: Human-facing label for a composite or control-flow block.
        location: Stable nested index path within the native circuit structure.
    """

    framework: str | None = None
    native_name: str | None = None
    native_kind: str | None = None
    grouping: str | None = None
    decomposition_origin: str | None = None
    composite_label: str | None = None
    location: tuple[int, ...] = ()


@dataclass(slots=True)
class SemanticOperationIR:
    """Operation-level semantic IR preserved before lowering to ``OperationIR``.

    Attributes:
        kind: ``OperationKind`` describing the drawable category.
        name: Stable operation name.
        target_wires: Quantum wire ids targeted by the operation.
        control_wires: Quantum wire ids used as controls.
        control_values: Accepted control values aligned with ``control_wires``.
        classical_conditions: Classical conditions that gate this operation.
        parameters: Display parameters, such as rotation angles.
        label: Optional visible label. ``None`` defaults to ``name``.
        canonical_family: Canonical rendering family, inferred from ``name`` when left
            as ``CUSTOM``.
        classical_target: Required classical target for measurements.
        annotations: Static text annotations rendered with the operation.
        hover_details: Extra hover text preserved from the adapter.
        provenance: Framework-native provenance for grouping and managed controls.
        metadata: Optional adapter metadata used by layout and rendering.
    """

    kind: OperationKind
    name: str
    target_wires: Sequence[str]
    control_wires: Sequence[str] = field(default_factory=tuple)
    control_values: Sequence[Sequence[int]] = field(default_factory=tuple)
    classical_conditions: Sequence[ClassicalConditionIR] = field(default_factory=tuple)
    parameters: Sequence[object] = field(default_factory=tuple)
    label: str | None = None
    canonical_family: CanonicalGateFamily = CanonicalGateFamily.CUSTOM
    classical_target: str | None = None
    annotations: Sequence[object] = field(default_factory=tuple)
    hover_details: Sequence[object] = field(default_factory=tuple)
    provenance: SemanticProvenanceIR = field(default_factory=SemanticProvenanceIR)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        self.name = normalized_name
        self.kind = _normalize_operation_kind(self.kind)
        self.target_wires = _normalize_wire_ids(self.target_wires)
        self.control_wires = _normalize_wire_ids(self.control_wires)
        self.control_values = _normalize_control_values(self.control_values)
        self.classical_conditions = _normalize_classical_conditions(self.classical_conditions)
        self.parameters = _normalize_parameters(self.parameters)
        self.annotations = _normalize_texts(self.annotations)
        self.hover_details = _normalize_texts(self.hover_details)
        self.canonical_family = _normalize_canonical_gate_family(self.canonical_family)
        if not normalized_name:
            raise ValueError("semantic operation name cannot be empty")
        if not self.target_wires and self.kind is not OperationKind.BARRIER:
            raise ValueError("semantic operation must reference at least one target wire")
        if self.control_values and len(self.control_values) != len(self.control_wires):
            raise ValueError("control_values must align with control_wires")
        if self.label is None:
            self.label = self.name
        if self.canonical_family is CanonicalGateFamily.CUSTOM:
            self.canonical_family = infer_canonical_gate_family(self.name)
        if self.kind is OperationKind.MEASUREMENT and self.classical_target is None:
            raise ValueError("semantic measurement operations require a classical_target")
        if self.classical_target is not None:
            self.classical_target = str(self.classical_target)
            if not self.classical_target:
                raise ValueError("semantic classical_target cannot be empty")

    @property
    def occupied_wire_ids(self) -> tuple[str, ...]:
        classical_wire_ids = tuple(
            wire_id for condition in self.classical_conditions for wire_id in condition.wire_ids
        )
        dependency_wire_ids = _metadata_wire_dependencies(self.metadata)
        occupied_wire_ids = tuple(
            dict.fromkeys(
                (*classical_wire_ids, *dependency_wire_ids, *self.control_wires, *self.target_wires)
            )
        )
        if self.classical_target is None:
            return occupied_wire_ids
        return tuple((*occupied_wire_ids, self.classical_target))


@dataclass(slots=True)
class SemanticLayerIR:
    """One layer of semantic operations before lowering.

    Attributes:
        operations: Semantic operations that can share one drawable time step.
        metadata: Optional layer-level metadata preserved from adapters.
    """

    operations: Sequence[SemanticOperationIR] = field(default_factory=tuple)
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.operations = tuple(self.operations)


@dataclass(slots=True)
class SemanticCircuitIR:
    """Circuit model that preserves native structure before render lowering.

    Attributes:
        quantum_wires: Ordered quantum wires.
        classical_wires: Ordered classical wires.
        layers: Ordered semantic layers.
        name: Optional circuit name.
        metadata: Optional circuit-level metadata preserved from adapters.
        diagnostics: Non-fatal adapter diagnostics that should travel with the circuit.
    """

    quantum_wires: Sequence[WireIR]
    classical_wires: Sequence[WireIR] = field(default_factory=tuple)
    layers: Sequence[SemanticLayerIR] = field(default_factory=tuple)
    name: str | None = None
    metadata: Metadata = field(default_factory=dict)
    diagnostics: Sequence[RenderDiagnostic] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        self.quantum_wires = tuple(self.quantum_wires)
        self.classical_wires = tuple(self.classical_wires)
        self.layers = tuple(self.layers)
        self.diagnostics = tuple(self.diagnostics)
        _validate_semantic_wire_group_kinds(self.quantum_wires, self.classical_wires)
        wire_ids = [wire.id for wire in self.all_wires]
        if len(wire_ids) != len(set(wire_ids)):
            raise ValueError("wire ids must be unique across semantic quantum and classical wires")
        wire_map = {wire.id: wire for wire in self.all_wires}
        _validate_semantic_operation_wire_references(self.layers, known_wire_ids=set(wire_ids))
        _validate_semantic_operation_wire_kinds(self.layers, wire_map=wire_map)

    @property
    def all_wires(self) -> tuple[WireIR, ...]:
        return tuple((*self.quantum_wires, *self.classical_wires))

    @property
    def wire_map(self) -> dict[str, WireIR]:
        return {wire.id: wire for wire in self.all_wires}


def _validate_semantic_wire_group_kinds(
    quantum_wires: tuple[WireIR, ...],
    classical_wires: tuple[WireIR, ...],
) -> None:
    if any(wire.kind is not WireKind.QUANTUM for wire in quantum_wires):
        raise ValueError("semantic quantum_wires must contain only quantum wires")
    if any(wire.kind is not WireKind.CLASSICAL for wire in classical_wires):
        raise ValueError("semantic classical_wires must contain only classical wires")


def _validate_semantic_operation_wire_references(
    layers: tuple[SemanticLayerIR, ...],
    *,
    known_wire_ids: set[str],
) -> None:
    for layer in layers:
        for operation in layer.operations:
            for wire_id in operation.occupied_wire_ids:
                if wire_id not in known_wire_ids:
                    raise ValueError(f"semantic operation references unknown wire id {wire_id!r}")


def _validate_semantic_operation_wire_kinds(
    layers: tuple[SemanticLayerIR, ...],
    *,
    wire_map: dict[str, WireIR],
) -> None:
    for layer in layers:
        for operation in layer.operations:
            _validate_semantic_wire_ids_have_kind(
                operation.control_wires,
                wire_map=wire_map,
                expected_kind=WireKind.QUANTUM,
                message="semantic operation control_wires must reference quantum wire ids",
            )
            for condition in operation.classical_conditions:
                _validate_semantic_wire_ids_have_kind(
                    condition.wire_ids,
                    wire_map=wire_map,
                    expected_kind=WireKind.CLASSICAL,
                    message=(
                        "semantic classical condition wire_ids must reference classical wire ids"
                    ),
                )
            if operation.kind is OperationKind.MEASUREMENT:
                _validate_semantic_wire_ids_have_kind(
                    operation.target_wires,
                    wire_map=wire_map,
                    expected_kind=WireKind.QUANTUM,
                    message="semantic measurement target_wires must reference quantum wire ids",
                )
            if operation.classical_target is not None:
                _validate_semantic_wire_ids_have_kind(
                    (operation.classical_target,),
                    wire_map=wire_map,
                    expected_kind=WireKind.CLASSICAL,
                    message=(
                        "semantic measurement classical_target must reference a classical wire id"
                    ),
                )


def _validate_semantic_wire_ids_have_kind(
    wire_ids: Sequence[str],
    *,
    wire_map: dict[str, WireIR],
    expected_kind: WireKind,
    message: str,
) -> None:
    if any(wire_map[wire_id].kind is not expected_kind for wire_id in wire_ids):
        raise ValueError(message)


def pack_semantic_operations(
    operations: Iterable[SemanticOperationIR],
    *,
    wire_order: Mapping[str, int] | None = None,
) -> tuple[SemanticLayerIR, ...]:
    """Pack semantic operations into layers without occupied-wire collisions.

    Args:
        operations: Semantic operations in source order.
        wire_order: Optional wire-id ordering used to reserve the full vertical span of
            expanded control-flow groups, preventing external gates from being packed
            visually inside a group box.

    Returns:
        Tuple of ``SemanticLayerIR`` objects where no operation in a layer occupies the
        same wire slot as another operation in that layer.
    """

    ordered_operations = list(operations)
    layer_operations: list[list[SemanticOperationIR]] = []
    latest_layer_by_slot: dict[str, int] = {}
    operation_index = 0
    while operation_index < len(ordered_operations):
        operation = ordered_operations[operation_index]
        group_id = _control_flow_group_id(operation)
        if group_id is None:
            _pack_single_semantic_operation(
                operation,
                layer_operations=layer_operations,
                latest_layer_by_slot=latest_layer_by_slot,
                slots=tuple(dict.fromkeys(operation.occupied_wire_ids)),
            )
            operation_index += 1
            continue

        group_operations: list[SemanticOperationIR] = []
        while operation_index < len(ordered_operations):
            grouped_operation = ordered_operations[operation_index]
            if _control_flow_group_id(grouped_operation) != group_id:
                break
            group_operations.append(grouped_operation)
            operation_index += 1

        _pack_control_flow_group_operations(
            group_operations,
            layer_operations=layer_operations,
            latest_layer_by_slot=latest_layer_by_slot,
            wire_order=wire_order,
        )
    return tuple(SemanticLayerIR(operations=layer) for layer in layer_operations)


def _pack_control_flow_group_operations(
    operations: Sequence[SemanticOperationIR],
    *,
    layer_operations: list[list[SemanticOperationIR]],
    latest_layer_by_slot: dict[str, int],
    wire_order: Mapping[str, int] | None,
) -> None:
    if not operations:
        return

    ignored_dependencies = _control_flow_group_dependency_wire_ids(operations[0])
    boundary_slots = _control_flow_group_boundary_slots(operations, wire_order=wire_order)
    start_layer = (
        max(
            (latest_layer_by_slot.get(slot, -1) for slot in boundary_slots),
            default=-1,
        )
        + 1
    )
    local_layers = _pack_control_flow_group_local_layers(
        operations,
        ignored_dependencies=ignored_dependencies,
    )
    for local_layer_index, local_layer in enumerate(local_layers):
        target_layer = start_layer + local_layer_index
        while len(layer_operations) <= target_layer:
            layer_operations.append([])
        layer_operations[target_layer].extend(local_layer)

    end_layer = start_layer + len(local_layers) - 1
    for slot in boundary_slots:
        latest_layer_by_slot[slot] = end_layer


def _pack_control_flow_group_local_layers(
    operations: Sequence[SemanticOperationIR],
    *,
    ignored_dependencies: frozenset[str],
) -> tuple[tuple[SemanticOperationIR, ...], ...]:
    local_layers: list[list[SemanticOperationIR]] = []
    latest_layer_by_slot: dict[str, int] = {}
    latest_layer_by_sequence_key: dict[tuple[str, ...], int] = {}
    for operation in operations:
        sequence_key = _nested_control_flow_sequence_key(operation)
        minimum_layer = _minimum_layer_for_control_flow_sequence(
            sequence_key,
            latest_layer_by_sequence_key,
        )
        target_layer = _pack_single_semantic_operation(
            operation,
            layer_operations=local_layers,
            latest_layer_by_slot=latest_layer_by_slot,
            slots=_local_control_flow_operation_slots(
                operation,
                ignored_dependencies=ignored_dependencies,
            ),
            minimum_layer=minimum_layer,
        )
        latest_layer_by_sequence_key[sequence_key] = max(
            target_layer,
            latest_layer_by_sequence_key.get(sequence_key, -1),
        )
    return tuple(tuple(layer) for layer in local_layers)


def _pack_single_semantic_operation(
    operation: SemanticOperationIR,
    *,
    layer_operations: list[list[SemanticOperationIR]],
    latest_layer_by_slot: dict[str, int],
    slots: tuple[str, ...],
    minimum_layer: int = 0,
) -> int:
    target_layer = max(
        max((latest_layer_by_slot.get(slot, -1) for slot in slots), default=-1) + 1,
        minimum_layer,
    )
    while len(layer_operations) <= target_layer:
        layer_operations.append([])
    layer_operations[target_layer].append(operation)
    for slot in slots:
        latest_layer_by_slot[slot] = target_layer
    return target_layer


def _minimum_layer_for_control_flow_sequence(
    sequence_key: tuple[str, ...],
    latest_layer_by_sequence_key: Mapping[tuple[str, ...], int],
) -> int:
    return (
        max(
            (
                latest_layer
                for key, latest_layer in latest_layer_by_sequence_key.items()
                if key != sequence_key
            ),
            default=-1,
        )
        + 1
    )


def _nested_control_flow_sequence_key(operation: SemanticOperationIR) -> tuple[str, ...]:
    stack_ids = _control_flow_group_stack_ids(operation.metadata)
    if len(stack_ids) <= 1:
        return ()
    return stack_ids[:-1]


def _local_control_flow_operation_slots(
    operation: SemanticOperationIR,
    *,
    ignored_dependencies: frozenset[str],
) -> tuple[str, ...]:
    classical_wire_ids = tuple(
        wire_id
        for condition in operation.classical_conditions
        for wire_id in condition.wire_ids
        if wire_id not in ignored_dependencies
    )
    dependency_wire_ids = tuple(
        wire_id
        for wire_id in _metadata_wire_dependencies(operation.metadata)
        if wire_id not in ignored_dependencies
    )
    occupied_wire_ids = tuple(
        dict.fromkeys(
            (
                *classical_wire_ids,
                *dependency_wire_ids,
                *operation.control_wires,
                *operation.target_wires,
            )
        )
    )
    if operation.classical_target is None:
        return occupied_wire_ids
    return tuple(dict.fromkeys((*occupied_wire_ids, operation.classical_target)))


def _control_flow_group_boundary_slots(
    operations: Sequence[SemanticOperationIR],
    *,
    wire_order: Mapping[str, int] | None,
) -> tuple[str, ...]:
    occupied_slots: list[str] = []
    quantum_slots: list[str] = []
    for operation in operations:
        occupied_slots.extend(operation.occupied_wire_ids)
        quantum_slots.extend(operation.control_wires)
        quantum_slots.extend(operation.target_wires)

    if wire_order is not None:
        occupied_slots.extend(_contiguous_ordered_slots(quantum_slots, wire_order))
    return tuple(dict.fromkeys(occupied_slots))


def _contiguous_ordered_slots(
    slots: Sequence[str],
    wire_order: Mapping[str, int],
) -> tuple[str, ...]:
    ordered_indices = [wire_order[slot] for slot in slots if slot in wire_order]
    if not ordered_indices:
        return ()

    first_index = min(ordered_indices)
    last_index = max(ordered_indices)
    return tuple(
        slot
        for slot, index in sorted(wire_order.items(), key=lambda entry: entry[1])
        if first_index <= index <= last_index
    )


def _control_flow_group_id(operation: SemanticOperationIR) -> str | None:
    group_metadata = operation.metadata.get("control_flow_group")
    if not isinstance(group_metadata, Mapping):
        return None
    group_id = group_metadata.get("id")
    if isinstance(group_id, str) and group_id:
        return group_id
    return None


def _control_flow_group_stack_ids(metadata: Metadata) -> tuple[str, ...]:
    stacked_groups = metadata.get("control_flow_groups")
    if isinstance(stacked_groups, Sequence) and not isinstance(stacked_groups, str | bytes):
        return tuple(
            str(group_id)
            for group in stacked_groups
            if isinstance(group, Mapping)
            and isinstance(group_id := group.get("id"), str)
            and group_id
        )

    group_metadata = metadata.get("control_flow_group")
    if isinstance(group_metadata, Mapping):
        group_id = group_metadata.get("id")
        if isinstance(group_id, str) and group_id:
            return (group_id,)
    return ()


def _control_flow_group_dependency_wire_ids(operation: SemanticOperationIR) -> frozenset[str]:
    group_metadata = operation.metadata.get("control_flow_group")
    if not isinstance(group_metadata, Mapping):
        return frozenset()

    dependency_wire_ids = set(_wire_dependency_metadata(group_metadata.get("wire_dependencies")))
    conditions = group_metadata.get("conditions")
    if isinstance(conditions, ClassicalConditionIR):
        dependency_wire_ids.update(conditions.wire_ids)
    elif isinstance(conditions, Sequence) and not isinstance(conditions, str | bytes):
        for condition in conditions:
            if isinstance(condition, ClassicalConditionIR):
                dependency_wire_ids.update(condition.wire_ids)
    return frozenset(dependency_wire_ids)


def _wire_dependency_metadata(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,) if value else ()
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(wire_id) for wire_id in value if str(wire_id))


def semantic_operation_signature(
    operation: SemanticOperationIR,
    wire_indices: dict[str, int],
) -> tuple[object, ...]:
    """Build a stable signature that preserves semantic operation differences.

    Args:
        operation: Semantic operation to summarize.
        wire_indices: Mapping from wire id to stable integer position.

    Returns:
        Tuple containing operation kind, canonical family, parameters, wires,
        conditions, annotations, hover details, and provenance fields.
    """

    measurement_target: int | str | None
    if operation.classical_target is None:
        measurement_target = None
    else:
        measurement_target = wire_indices.get(
            operation.classical_target, operation.classical_target
        )
    return (
        operation.kind,
        operation.canonical_family,
        operation.name,
        tuple(_parameter_signature_token(parameter) for parameter in operation.parameters),
        tuple(wire_indices[wire_id] for wire_id in operation.target_wires),
        tuple(wire_indices[wire_id] for wire_id in operation.control_wires),
        tuple(tuple(int(value) for value in entry) for entry in operation.control_values),
        tuple(
            (
                tuple(wire_indices.get(wire_id, wire_id) for wire_id in condition.wire_ids),
                condition.expression,
            )
            for condition in operation.classical_conditions
        ),
        measurement_target,
        operation.annotations,
        operation.hover_details,
        operation.provenance.framework,
        operation.provenance.native_name,
        operation.provenance.native_kind,
        operation.provenance.grouping,
        operation.provenance.decomposition_origin,
        operation.provenance.composite_label,
        operation.provenance.location,
    )


def semantic_operation_id(operation: SemanticOperationIR) -> str:
    """Return the stable semantic identifier for one operation.

    Args:
        operation: Semantic operation whose id should be resolved.

    Returns:
        Explicit ``semantic_operation_id`` metadata when present, otherwise an id from
        provenance location, otherwise a deterministic fallback from name and targets.
    """

    explicit_id = operation.metadata.get("semantic_operation_id")
    if isinstance(explicit_id, str) and explicit_id:
        return explicit_id
    if operation.provenance.location:
        return semantic_operation_id_from_location(operation.provenance.location)
    fallback_wire_token = ",".join(operation.target_wires)
    return f"op:unlocated:{operation.name}:{fallback_wire_token}"
