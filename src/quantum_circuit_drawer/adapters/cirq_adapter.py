"""Cirq adapter."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import replace
from math import isclose
from typing import Any, Protocol, cast

from ..diagnostics import DiagnosticSeverity, RenderDiagnostic
from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.operations import OperationKind
from ..ir.semantic import SemanticCircuitIR, SemanticLayerIR, SemanticOperationIR
from ..ir.wires import WireIR, WireKind
from ..utils.matrix_support import square_matrix
from ._helpers import (
    CanonicalGateSpec,
    append_semantic_classical_conditions,
    build_classical_register,
    canonical_gate_spec,
    extract_dependency_types,
    is_expected_matrix_unavailable_error,
    normalized_detail_lines,
    resolve_composite_mode,
    resolve_explicit_matrices,
    resolve_wire_ids,
    semantic_provenance,
    sequential_bit_labels,
)
from .base import BaseAdapter


class _CirqOperationLike(Protocol):
    qubits: Sequence[object]


class _CirqMomentLike(Protocol):
    operations: Sequence[_CirqOperationLike]


class _CirqCircuitLike(Protocol):
    def all_qubits(self) -> Iterable[object]: ...

    def __iter__(self) -> Iterator[_CirqMomentLike]: ...


class CirqAdapter(BaseAdapter):
    """Convert cirq.Circuit objects into CircuitIR."""

    framework_name = "cirq"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        circuit_types = extract_dependency_types("cirq", ("Circuit",))
        return bool(circuit_types) and isinstance(circuit, circuit_types)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        semantic_ir = self.to_semantic_ir(circuit, options=options)
        assert semantic_ir is not None
        return lower_semantic_circuit(semantic_ir)

    def to_semantic_ir(
        self,
        circuit: object,
        options: Mapping[str, object] | None = None,
    ) -> SemanticCircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("CirqAdapter received a non-Cirq circuit")

        import cirq

        typed_circuit = cast(_CirqCircuitLike, circuit)
        composite_mode = resolve_composite_mode(options)
        explicit_matrices = resolve_explicit_matrices(options)
        qubits = sorted(typed_circuit.all_qubits(), key=str)
        qubit_ids = resolve_wire_ids(qubits, prefix="q")
        quantum_wires = [
            WireIR(id=qubit_ids[qubit], index=index, kind=WireKind.QUANTUM, label=str(qubit))
            for index, qubit in enumerate(qubits)
        ]

        measurement_slots: dict[tuple[int, ...], tuple[tuple[str, str], ...]] = {}
        measurement_key_targets: dict[str, tuple[tuple[str, str], ...]] = {}
        measurement_labels: list[str] = []
        for moment_index, moment in enumerate(typed_circuit):
            for operation_index, operation in enumerate(moment.operations):
                self._collect_measurement_targets(
                    cirq=cirq,
                    operation=operation,
                    measurement_slots=measurement_slots,
                    measurement_key_targets=measurement_key_targets,
                    measurement_labels=measurement_labels,
                    operation_key=(moment_index, operation_index),
                    composite_mode=composite_mode,
                )

        classical_wires, _ = build_classical_register(
            sequential_bit_labels(len(measurement_labels))
        )

        diagnostics: list[RenderDiagnostic] = []
        semantic_layers: list[SemanticLayerIR] = []
        for moment_index, moment in enumerate(typed_circuit):
            semantic_layers.extend(
                self._convert_moment(
                    cirq=cirq,
                    moment=moment,
                    qubit_ids=qubit_ids,
                    measurement_slots=measurement_slots,
                    measurement_key_targets=measurement_key_targets,
                    moment_index=moment_index,
                    grouping=f"moment[{moment_index}]",
                    composite_mode=composite_mode,
                    explicit_matrices=explicit_matrices,
                    diagnostics=diagnostics,
                )
            )

        return SemanticCircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=tuple(semantic_layers),
            metadata={"framework": self.framework_name},
            diagnostics=tuple(diagnostics),
        )

    def _convert_moment(
        self,
        *,
        cirq: Any,
        moment: _CirqMomentLike,
        qubit_ids: dict[object, str],
        measurement_slots: dict[tuple[int, ...], tuple[tuple[str, str], ...]],
        measurement_key_targets: dict[str, tuple[tuple[str, str], ...]],
        moment_index: int,
        grouping: str,
        composite_mode: str,
        explicit_matrices: bool,
        diagnostics: list[RenderDiagnostic],
    ) -> tuple[SemanticLayerIR, ...]:
        grouped_operations: list[list[SemanticOperationIR]] = []
        layer_metadata: list[dict[str, object]] = []
        for operation_index, operation in enumerate(moment.operations):
            converted_layers = self._convert_operation(
                cirq=cirq,
                operation=operation,
                qubit_ids=qubit_ids,
                measurement_slots=measurement_slots,
                measurement_key_targets=measurement_key_targets,
                operation_key=(moment_index, operation_index),
                grouping=grouping,
                composite_mode=composite_mode,
                explicit_matrices=explicit_matrices,
                diagnostics=diagnostics,
            )
            for layer_index, converted_layer in enumerate(converted_layers):
                while len(grouped_operations) <= layer_index:
                    grouped_operations.append([])
                    layer_metadata.append(dict(converted_layer.metadata))
                grouped_operations[layer_index].extend(converted_layer.operations)
                layer_metadata[layer_index].update(converted_layer.metadata)
        return tuple(
            SemanticLayerIR(operations=operations, metadata=metadata)
            for operations, metadata in zip(grouped_operations, layer_metadata, strict=True)
        )

    def _collect_measurement_targets(
        self,
        *,
        cirq: Any,
        operation: _CirqOperationLike,
        measurement_slots: dict[tuple[int, ...], tuple[tuple[str, str], ...]],
        measurement_key_targets: dict[str, tuple[tuple[str, str], ...]],
        measurement_labels: list[str],
        operation_key: tuple[int, ...],
        composite_mode: str,
    ) -> None:
        if self._is_measurement(operation):
            key_targets: list[tuple[str, str]] = []
            for _ in operation.qubits:
                measurement_labels.append(f"c[{len(measurement_labels)}]")
                key_targets.append(("c0", measurement_labels[-1]))
            measurement_slots[operation_key] = tuple(key_targets)
            measurement_key_targets[str(self._measurement_key(operation))] = tuple(key_targets)
            return

        if isinstance(operation, cirq.ClassicallyControlledOperation):
            base_operation = cast(
                _CirqOperationLike,
                operation.without_classical_controls(),
            )
            self._collect_measurement_targets(
                cirq=cirq,
                operation=base_operation,
                measurement_slots=measurement_slots,
                measurement_key_targets=measurement_key_targets,
                measurement_labels=measurement_labels,
                operation_key=operation_key,
                composite_mode=composite_mode,
            )
            return

        if not isinstance(operation, cirq.CircuitOperation) or composite_mode != "expand":
            return

        for nested_moment_index, moment in enumerate(operation.mapped_circuit()):
            for nested_operation_index, nested_operation in enumerate(moment.operations):
                self._collect_measurement_targets(
                    cirq=cirq,
                    operation=cast(_CirqOperationLike, nested_operation),
                    measurement_slots=measurement_slots,
                    measurement_key_targets=measurement_key_targets,
                    measurement_labels=measurement_labels,
                    operation_key=(
                        *operation_key,
                        nested_moment_index,
                        nested_operation_index,
                    ),
                    composite_mode=composite_mode,
                )

    def _convert_operation(
        self,
        *,
        cirq: Any,
        operation: _CirqOperationLike,
        qubit_ids: dict[object, str],
        measurement_slots: dict[tuple[int, ...], tuple[tuple[str, str], ...]],
        measurement_key_targets: dict[str, tuple[tuple[str, str], ...]],
        operation_key: tuple[int, ...],
        grouping: str,
        composite_mode: str,
        explicit_matrices: bool,
        diagnostics: list[RenderDiagnostic],
    ) -> tuple[SemanticLayerIR, ...]:
        if self._is_measurement(operation):
            converted: list[SemanticOperationIR] = []
            slot_targets = measurement_slots.get(operation_key)
            if slot_targets is None:
                raise UnsupportedOperationError(
                    "Cirq measurement was not registered before conversion"
                )
            for qubit, (classical_target, classical_bit_label) in zip(
                operation.qubits,
                slot_targets,
                strict=True,
            ):
                converted.append(
                    SemanticOperationIR(
                        kind=OperationKind.MEASUREMENT,
                        name="M",
                        target_wires=(qubit_ids[qubit],),
                        classical_target=classical_target,
                        hover_details=normalized_detail_lines(f"group: {grouping}"),
                        provenance=semantic_provenance(
                            framework=self.framework_name,
                            native_name="MeasurementGate",
                            native_kind="measurement",
                            grouping=grouping,
                            location=operation_key,
                        ),
                        metadata={"classical_bit_label": classical_bit_label},
                    )
                )
            return (
                SemanticLayerIR(
                    operations=tuple(converted),
                    metadata={"native_group": grouping},
                ),
            )

        if isinstance(operation, cirq.ClassicallyControlledOperation):
            base_operation = cast(
                _CirqOperationLike,
                operation.without_classical_controls(),
            )
            conditions = self._classical_conditions_for_controls(
                operation.classical_controls,
                measurement_key_targets,
            )
            converted = self._convert_operation(
                cirq=cirq,
                operation=base_operation,
                qubit_ids=qubit_ids,
                measurement_slots=measurement_slots,
                measurement_key_targets=measurement_key_targets,
                operation_key=operation_key,
                grouping=grouping,
                composite_mode=composite_mode,
                explicit_matrices=explicit_matrices,
                diagnostics=diagnostics,
            )
            conditioned_layers: list[SemanticLayerIR] = []
            condition_details = tuple(
                f"conditional on: {condition.expression}" for condition in conditions
            )
            for layer in converted:
                conditioned_layers.append(
                    SemanticLayerIR(
                        operations=tuple(
                            replace(
                                append_semantic_classical_conditions(node, conditions),
                                hover_details=(*node.hover_details, *condition_details),
                            )
                            for node in layer.operations
                        ),
                        metadata=layer.metadata,
                    )
                )
            return tuple(conditioned_layers)

        if isinstance(operation, cirq.CircuitOperation):
            if composite_mode == "expand":
                nested_layers: list[SemanticLayerIR] = []
                nested_grouping = f"{grouping}/CircuitOperation[{operation_key[-1]}]"
                for nested_moment_index, nested_moment in enumerate(operation.mapped_circuit()):
                    nested_layers.extend(
                        self._convert_moment(
                            cirq=cirq,
                            moment=nested_moment,
                            qubit_ids=qubit_ids,
                            measurement_slots=measurement_slots,
                            measurement_key_targets=measurement_key_targets,
                            moment_index=operation_key[0],
                            grouping=f"{nested_grouping}/moment[{nested_moment_index}]",
                            composite_mode=composite_mode,
                            explicit_matrices=explicit_matrices,
                            diagnostics=diagnostics,
                        )
                    )
                lowered_layers: list[SemanticLayerIR] = []
                for nested_layer in nested_layers:
                    lowered_layers.append(
                        SemanticLayerIR(
                            operations=tuple(
                                replace(
                                    node,
                                    hover_details=(
                                        *node.hover_details,
                                        *normalized_detail_lines(
                                            "decomposed from: CircuitOperation",
                                        ),
                                    ),
                                    provenance=semantic_provenance(
                                        framework=self.framework_name,
                                        native_name=node.provenance.native_name or node.name,
                                        native_kind=node.provenance.native_kind,
                                        grouping=node.provenance.grouping,
                                        decomposition_origin="CircuitOperation",
                                        composite_label="CircuitOperation",
                                        location=node.provenance.location,
                                    ),
                                )
                                for node in nested_layer.operations
                            ),
                            metadata=nested_layer.metadata,
                        )
                    )
                return tuple(lowered_layers)
            diagnostics.append(
                RenderDiagnostic(
                    code="cirq_circuit_operation_compact_render",
                    message=(
                        "Rendered a Cirq CircuitOperation as one compact box; "
                        "use composite_mode='expand' to preserve inner structure."
                    ),
                    severity=DiagnosticSeverity.INFO,
                )
            )
            return (
                SemanticLayerIR(
                    operations=(
                        SemanticOperationIR(
                            kind=OperationKind.GATE,
                            name=operation.__class__.__name__,
                            label=operation.__class__.__name__,
                            target_wires=tuple(qubit_ids[qubit] for qubit in operation.qubits),
                            annotations=("CircuitOperation",),
                            hover_details=normalized_detail_lines(
                                f"group: {grouping}",
                                "native: CircuitOperation",
                            ),
                            provenance=semantic_provenance(
                                framework=self.framework_name,
                                native_name="CircuitOperation",
                                native_kind="composite",
                                grouping=grouping,
                                composite_label="CircuitOperation",
                                location=operation_key,
                            ),
                            metadata=self._matrix_metadata(
                                cirq=cirq,
                                operation=operation,
                                explicit_matrices=explicit_matrices,
                            ),
                        ),
                    ),
                    metadata={"native_group": grouping},
                ),
            )

        gate = getattr(operation, "gate", None)
        class_name = (
            gate.__class__.__name__.lower()
            if gate is not None
            else operation.__class__.__name__.lower()
        )
        target_wires = tuple(qubit_ids[qubit] for qubit in operation.qubits)

        if isinstance(operation, cirq.ControlledOperation):
            controlled_operation = cast(Any, operation)
            controls = tuple(qubit_ids[qubit] for qubit in controlled_operation.controls)
            targets = tuple(qubit_ids[qubit] for qubit in controlled_operation.sub_operation.qubits)
            canonical_gate, parameters = self._canonical_gate_for_operation(
                controlled_operation.sub_operation
            )
            return self._semantic_gate_layer(
                kind=OperationKind.CONTROLLED_GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=targets,
                control_wires=controls,
                control_values=self._control_values_for_controlled_operation(controlled_operation),
                parameters=parameters,
                grouping=grouping,
                operation_key=operation_key,
                native_name=self._raw_operation_name(controlled_operation.sub_operation),
                native_kind="controlled_operation",
                matrix_metadata=self._matrix_metadata(
                    cirq=cirq,
                    operation=operation,
                    explicit_matrices=explicit_matrices,
                ),
            )

        if class_name in {"cxpowgate", "cnotpowgate", "ccxpowgate"}:
            control_count = (
                1 if class_name in {"cxpowgate", "cnotpowgate"} else len(target_wires) - 1
            )
            canonical_gate = canonical_gate_spec("CNOT" if control_count == 1 else "TOFFOLI")
            return self._semantic_gate_layer(
                kind=OperationKind.CONTROLLED_GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=(target_wires[-1],),
                control_wires=target_wires[:control_count],
                parameters=self._extract_parameters(gate),
                grouping=grouping,
                operation_key=operation_key,
                native_name=self._raw_operation_name(operation),
                native_kind="controlled_gate",
                matrix_metadata=self._matrix_metadata(
                    cirq=cirq,
                    operation=operation,
                    explicit_matrices=explicit_matrices,
                ),
            )
        if class_name == "czpowgate":
            canonical_gate = canonical_gate_spec("CZ")
            return self._semantic_gate_layer(
                kind=OperationKind.CONTROLLED_GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=(target_wires[1],),
                control_wires=(target_wires[0],),
                parameters=self._extract_parameters(gate),
                grouping=grouping,
                operation_key=operation_key,
                native_name=self._raw_operation_name(operation),
                native_kind="controlled_gate",
                matrix_metadata=self._matrix_metadata(
                    cirq=cirq,
                    operation=operation,
                    explicit_matrices=explicit_matrices,
                ),
            )
        if class_name == "swappowgate":
            return self._semantic_gate_layer(
                kind=OperationKind.SWAP,
                name="SWAP",
                canonical_family=canonical_gate_spec("SWAP").family,
                target_wires=target_wires,
                control_wires=(),
                parameters=(),
                grouping=grouping,
                operation_key=operation_key,
                native_name=self._raw_operation_name(operation),
                native_kind="swap",
                matrix_metadata=self._matrix_metadata(
                    cirq=cirq,
                    operation=operation,
                    explicit_matrices=explicit_matrices,
                ),
            )

        canonical_gate, parameters = self._canonical_gate_for_operation(operation)
        return self._semantic_gate_layer(
            kind=OperationKind.GATE,
            name=canonical_gate.label,
            canonical_family=canonical_gate.family,
            target_wires=target_wires,
            control_wires=(),
            parameters=parameters,
            grouping=grouping,
            operation_key=operation_key,
            native_name=self._raw_operation_name(operation),
            native_kind="gate",
            matrix_metadata=self._matrix_metadata(
                cirq=cirq,
                operation=operation,
                explicit_matrices=explicit_matrices,
            ),
        )

    def _semantic_gate_layer(
        self,
        *,
        kind: OperationKind,
        name: str,
        canonical_family: object,
        target_wires: tuple[str, ...],
        control_wires: tuple[str, ...],
        control_values: tuple[tuple[int, ...], ...] = (),
        parameters: tuple[object, ...],
        grouping: str,
        operation_key: tuple[int, ...],
        native_name: str,
        native_kind: str,
        matrix_metadata: dict[str, object],
    ) -> tuple[SemanticLayerIR, ...]:
        return (
            SemanticLayerIR(
                operations=(
                    SemanticOperationIR(
                        kind=kind,
                        name=name,
                        canonical_family=canonical_family,
                        target_wires=target_wires,
                        control_wires=control_wires,
                        control_values=control_values,
                        parameters=parameters,
                        hover_details=normalized_detail_lines(f"group: {grouping}"),
                        provenance=semantic_provenance(
                            framework=self.framework_name,
                            native_name=native_name,
                            native_kind=native_kind,
                            grouping=grouping,
                            location=operation_key,
                        ),
                        metadata=matrix_metadata,
                    ),
                ),
                metadata={"native_group": grouping},
            ),
        )

    def _matrix_metadata(
        self,
        *,
        cirq: Any,
        operation: object,
        explicit_matrices: bool = True,
    ) -> dict[str, object]:
        if not explicit_matrices:
            return {}

        try:
            matrix = cirq.unitary(operation, default=None)
        except Exception as exc:
            if not is_expected_matrix_unavailable_error(exc):
                raise
            return {}

        if matrix is None or square_matrix(matrix) is None:
            return {}
        return {"matrix": matrix}

    def _is_measurement(self, operation: object) -> bool:
        gate = getattr(operation, "gate", None)
        return gate is not None and gate.__class__.__name__ == "MeasurementGate"

    def _measurement_key(self, operation: object) -> object:
        gate = getattr(operation, "gate", None)
        return getattr(gate, "key", None)

    def _classical_conditions_for_controls(
        self,
        controls: Sequence[object],
        measurement_key_targets: dict[str, tuple[tuple[str, str], ...]],
    ) -> tuple[ClassicalConditionIR, ...]:
        conditions: list[ClassicalConditionIR] = []
        for control in controls:
            key = getattr(control, "key", None)
            key_targets = measurement_key_targets.get(str(key))
            if key is None or not key_targets:
                raise UnsupportedOperationError("unsupported Cirq classical condition")
            raw_value = getattr(control, "value", None)
            value = 1 if raw_value is None else int(raw_value)
            index = getattr(control, "index", None)
            if index is not None:
                index_value = int(index)
                if index_value < 0 or index_value >= len(key_targets):
                    raise UnsupportedOperationError("unsupported Cirq classical condition index")
                wire_id, bit_label = key_targets[index_value]
                wire_ids = (wire_id,)
                expression = f"if {bit_label}={value}"
            else:
                wire_ids = tuple(dict.fromkeys(wire_id for wire_id, _ in key_targets))
                if len(key_targets) == 1:
                    _, bit_label = key_targets[0]
                    expression = f"if {bit_label}={value}"
                else:
                    expression = f"if c={value}"
            conditions.append(ClassicalConditionIR(wire_ids=wire_ids, expression=expression))
        return tuple(conditions)

    def _control_values_for_controlled_operation(
        self,
        controlled_operation: object,
    ) -> tuple[tuple[int, ...], ...]:
        raw_values = getattr(controlled_operation, "control_values", ())
        expand = getattr(raw_values, "expand", None)
        if callable(expand):
            raw_values = expand()
        if raw_values is None:
            return ()

        normalized_entries: list[tuple[int, ...]] = []
        for raw_entry in tuple(raw_values):
            if isinstance(raw_entry, Sequence) and not isinstance(raw_entry, str | bytes):
                values = tuple(int(value) for value in raw_entry)
            else:
                values = (int(raw_entry),)
            normalized_entries.append(values)
        if all(entry == (1,) for entry in normalized_entries):
            return ()
        return tuple(normalized_entries)

    def _canonical_gate_for_operation(
        self,
        operation: object,
    ) -> tuple[CanonicalGateSpec, tuple[object, ...]]:
        gate = getattr(operation, "gate", None)
        if gate is None:
            return canonical_gate_spec(operation.__class__.__name__), ()

        special_label = self._special_canonical_label(gate)
        if special_label is not None:
            return canonical_gate_spec(special_label), ()

        return canonical_gate_spec(self._raw_operation_name(operation)), self._extract_parameters(
            gate
        )

    def _special_canonical_label(self, gate: object) -> str | None:
        exponent = getattr(gate, "exponent", None)
        if exponent is None:
            return None
        try:
            exponent_value = float(exponent)
        except (TypeError, ValueError):
            return None

        class_name = gate.__class__.__name__.lower()
        if class_name == "xpowgate":
            if isclose(exponent_value, 0.5, rel_tol=0.0, abs_tol=1e-9):
                return "SX"
            if isclose(exponent_value, -0.5, rel_tol=0.0, abs_tol=1e-9):
                return "SXdg"
            return None

        if class_name == "zpowgate":
            special_labels = {
                0.5: "S",
                -0.5: "Sdg",
                0.25: "T",
                -0.25: "Tdg",
            }
            for special_exponent, label in special_labels.items():
                if isclose(exponent_value, special_exponent, rel_tol=0.0, abs_tol=1e-9):
                    return label
        return None

    def _raw_operation_name(self, operation: object) -> str:
        gate = getattr(operation, "gate", None)
        if gate is None:
            return operation.__class__.__name__
        class_name = gate.__class__.__name__.lower()
        mapping = {
            "identitygate": "I",
            "hpowgate": "H",
            "xpowgate": "X",
            "ypowgate": "Y",
            "zpowgate": "Z",
            "cnotpowgate": "CNOT",
            "cxpowgate": "CX",
            "ccxpowgate": "TOFFOLI",
            "czpowgate": "CZ",
            "swappowgate": "SWAP",
            "iswappowgate": "iSWAP",
            "resetchannel": "RESET",
            "xxpowgate": "RXX",
            "yypowgate": "RYY",
            "zzpowgate": "RZZ",
            "fsimgate": "FSIM",
        }
        return mapping.get(class_name, str(gate))

    def _extract_parameters(self, gate: object) -> tuple[object, ...]:
        if gate is None:
            return ()
        values: list[object] = []
        for attribute in ("theta", "phi", "lam", "exponent"):
            if not hasattr(gate, attribute):
                continue
            value = getattr(gate, attribute)
            if attribute == "exponent" and value == 1:
                continue
            values.append(value)
        return tuple(values)
