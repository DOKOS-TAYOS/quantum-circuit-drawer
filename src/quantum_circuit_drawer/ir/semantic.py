"""Semantic circuit IR that preserves framework-native structure and provenance."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from ..diagnostics import RenderDiagnostic
from ..typing import Metadata
from .classical_conditions import ClassicalConditionIR
from .operations import (
    CanonicalGateFamily,
    OperationKind,
    _normalize_control_values,
    infer_canonical_gate_family,
)
from .wires import WireIR


def _normalize_wire_ids(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


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
        return (value,)
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
        self.target_wires = _normalize_wire_ids(self.target_wires)
        self.control_wires = _normalize_wire_ids(self.control_wires)
        self.control_values = _normalize_control_values(self.control_values)
        self.classical_conditions = _normalize_classical_conditions(self.classical_conditions)
        self.parameters = _normalize_parameters(self.parameters)
        self.annotations = _normalize_texts(self.annotations)
        self.hover_details = _normalize_texts(self.hover_details)
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
        wire_ids = [wire.id for wire in self.all_wires]
        if len(wire_ids) != len(set(wire_ids)):
            raise ValueError("wire ids must be unique across semantic quantum and classical wires")

    @property
    def all_wires(self) -> tuple[WireIR, ...]:
        return tuple((*self.quantum_wires, *self.classical_wires))

    @property
    def wire_map(self) -> dict[str, WireIR]:
        return {wire.id: wire for wire in self.all_wires}


def pack_semantic_operations(
    operations: Iterable[SemanticOperationIR],
) -> tuple[SemanticLayerIR, ...]:
    """Pack semantic operations into layers without occupied-wire collisions.

    Args:
        operations: Semantic operations in source order.

    Returns:
        Tuple of ``SemanticLayerIR`` objects where no operation in a layer occupies the
        same wire slot as another operation in that layer.
    """

    layer_operations: list[list[SemanticOperationIR]] = []
    latest_layer_by_slot: dict[str, int] = {}
    for operation in operations:
        slots = tuple(dict.fromkeys(operation.occupied_wire_ids))
        target_layer = max((latest_layer_by_slot.get(slot, -1) for slot in slots), default=-1) + 1
        while len(layer_operations) <= target_layer:
            layer_operations.append([])
        layer_operations[target_layer].append(operation)
        for slot in slots:
            latest_layer_by_slot[slot] = target_layer
    return tuple(SemanticLayerIR(operations=layer) for layer in layer_operations)


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
