"""Lowering helpers between semantic IR and render-focused ``CircuitIR``."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .circuit import CircuitIR, LayerIR
from .classical_conditions import ClassicalConditionIR
from .measurements import MeasurementIR
from .operations import CanonicalGateFamily, OperationIR, OperationKind
from .semantic import (
    SemanticCircuitIR,
    SemanticLayerIR,
    SemanticOperationIR,
    SemanticProvenanceIR,
)


@dataclass(frozen=True, slots=True)
class _LoweredOperationPayload:
    kind: OperationKind
    name: str
    target_wires: tuple[str, ...]
    control_wires: tuple[str, ...]
    control_values: tuple[tuple[int, ...], ...]
    classical_conditions: tuple[ClassicalConditionIR, ...]
    parameters: tuple[object, ...]
    label: str | None
    canonical_family: CanonicalGateFamily
    metadata: dict[str, object]


def lower_semantic_circuit(circuit: SemanticCircuitIR) -> CircuitIR:
    """Lower semantic IR into the existing render-focused ``CircuitIR`` contract."""

    return CircuitIR(
        quantum_wires=circuit.quantum_wires,
        classical_wires=circuit.classical_wires,
        layers=tuple(lower_semantic_layer(layer) for layer in circuit.layers),
        name=circuit.name,
        metadata=dict(circuit.metadata),
    )


def lower_semantic_layer(layer: SemanticLayerIR) -> LayerIR:
    """Lower one semantic layer into a render-focused ``LayerIR``."""

    return LayerIR(
        operations=tuple(lower_semantic_operation(operation) for operation in layer.operations),
        metadata=dict(layer.metadata),
    )


def lower_semantic_operation(operation: SemanticOperationIR) -> OperationIR | MeasurementIR:
    """Lower one semantic operation into the existing render-focused operation IR."""

    payload = lowered_operation_payload(operation)
    if operation.kind is OperationKind.MEASUREMENT:
        return MeasurementIR(
            kind=payload.kind,
            name=payload.name,
            target_wires=payload.target_wires,
            control_wires=payload.control_wires,
            control_values=payload.control_values,
            classical_conditions=payload.classical_conditions,
            parameters=payload.parameters,
            label=payload.label,
            canonical_family=payload.canonical_family,
            metadata=payload.metadata,
            classical_target=operation.classical_target,
        )
    return OperationIR(
        kind=payload.kind,
        name=payload.name,
        target_wires=payload.target_wires,
        control_wires=payload.control_wires,
        control_values=payload.control_values,
        classical_conditions=payload.classical_conditions,
        parameters=payload.parameters,
        label=payload.label,
        canonical_family=payload.canonical_family,
        metadata=payload.metadata,
    )


def semantic_circuit_from_circuit_ir(circuit: CircuitIR) -> SemanticCircuitIR:
    """Wrap legacy ``CircuitIR`` values as semantic IR without changing behavior."""

    framework_name = str(circuit.metadata.get("framework", "ir"))
    return SemanticCircuitIR(
        quantum_wires=circuit.quantum_wires,
        classical_wires=circuit.classical_wires,
        layers=tuple(
            semantic_layer_from_layer_ir(layer, framework_name=framework_name)
            for layer in circuit.layers
        ),
        name=circuit.name,
        metadata=dict(circuit.metadata),
    )


def semantic_layer_from_layer_ir(
    layer: LayerIR,
    *,
    framework_name: str,
) -> SemanticLayerIR:
    """Wrap one legacy ``LayerIR`` as a semantic layer."""

    return SemanticLayerIR(
        operations=tuple(
            semantic_operation_from_operation_ir(operation, framework_name=framework_name)
            for operation in layer.operations
        ),
        metadata=dict(layer.metadata),
    )


def semantic_operation_from_operation_ir(
    operation: OperationIR | MeasurementIR,
    *,
    framework_name: str,
) -> SemanticOperationIR:
    """Wrap one legacy operation as semantic IR."""

    provenance = SemanticProvenanceIR(
        framework=framework_name,
        native_name=_optional_string(operation.metadata.get("native_name")),
    )
    return SemanticOperationIR(
        kind=operation.kind,
        name=operation.name,
        target_wires=operation.target_wires,
        control_wires=operation.control_wires,
        control_values=operation.control_values,
        classical_conditions=operation.classical_conditions,
        parameters=operation.parameters,
        label=operation.label,
        canonical_family=operation.canonical_family,
        classical_target=(
            operation.classical_target if isinstance(operation, MeasurementIR) else None
        ),
        annotations=_string_tuple(operation.metadata.get("native_annotations")),
        hover_details=_string_tuple(operation.metadata.get("hover_details")),
        provenance=provenance,
        metadata=dict(operation.metadata),
    )


def provenance_metadata(provenance: SemanticProvenanceIR) -> dict[str, object]:
    """Convert provenance to a plain metadata mapping for lowered operations."""

    return dict(asdict(provenance))


def lowered_operation_payload(operation: SemanticOperationIR) -> _LoweredOperationPayload:
    """Build the typed render-IR payload for one semantic operation."""

    metadata = dict(operation.metadata)
    if operation.annotations:
        metadata["native_annotations"] = tuple(operation.annotations)
    if operation.hover_details:
        metadata["hover_details"] = tuple(operation.hover_details)
    metadata["semantic_provenance"] = provenance_metadata(operation.provenance)

    return _LoweredOperationPayload(
        kind=operation.kind,
        name=operation.name,
        target_wires=tuple(operation.target_wires),
        control_wires=tuple(operation.control_wires),
        control_values=tuple(tuple(values) for values in operation.control_values),
        classical_conditions=tuple(operation.classical_conditions),
        parameters=tuple(operation.parameters),
        label=operation.label,
        canonical_family=operation.canonical_family,
        metadata=metadata,
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple | list):
        return ()
    return tuple(str(item) for item in value if str(item))


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
