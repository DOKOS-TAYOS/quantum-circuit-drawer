"""Qiskit adapter."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol, cast

from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.lowering import lower_semantic_circuit
from ..ir.operations import OperationKind
from ..ir.semantic import SemanticCircuitIR, SemanticOperationIR, pack_semantic_operations
from ..ir.wires import WireIR, WireKind
from ..utils.matrix_support import square_matrix
from ._helpers import (
    append_semantic_classical_conditions,
    canonical_gate_spec,
    extract_dependency_types,
    is_expected_matrix_unavailable_error,
    normalized_detail_lines,
    resolve_composite_mode,
    resolve_explicit_matrices,
    semantic_provenance,
)
from .base import BaseAdapter


class _QiskitRegisterLike(Protocol):
    name: str | None

    def __iter__(self) -> Iterable[object]: ...


class _QiskitCircuitLike(Protocol):
    qubits: Sequence[object]
    clbits: Sequence[object]
    data: Sequence[object]
    cregs: Sequence[_QiskitRegisterLike]
    name: str | None


class QiskitAdapter(BaseAdapter):
    """Convert qiskit.QuantumCircuit objects into CircuitIR."""

    framework_name = "qiskit"
    _CONTROL_FLOW_LABELS: dict[str, str] = {
        "if_else": "IF/ELSE",
        "switch_case": "SWITCH",
        "for_loop": "FOR",
        "while_loop": "WHILE",
    }

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        circuit_types = extract_dependency_types("qiskit", ("circuit.QuantumCircuit",))
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
            raise TypeError("QiskitAdapter received a non-Qiskit circuit")

        typed_circuit = cast(_QiskitCircuitLike, circuit)
        composite_mode = resolve_composite_mode(options)
        explicit_matrices = resolve_explicit_matrices(options)
        qubits = list(typed_circuit.qubits)
        clbits = list(typed_circuit.clbits)
        qubit_ids = {bit: f"q{index}" for index, bit in enumerate(qubits)}
        classical_wires, classical_targets, register_targets = self._build_classical_wires(
            typed_circuit,
            clbits,
        )

        quantum_wires = [
            WireIR(id=qubit_ids[bit], index=index, kind=WireKind.QUANTUM, label=f"q{index}")
            for index, bit in enumerate(qubits)
        ]

        operations: list[SemanticOperationIR] = []
        for instruction_index, entry in enumerate(typed_circuit.data):
            operations.extend(
                self._convert_instruction(
                    entry,
                    qubit_ids,
                    classical_targets,
                    register_targets,
                    composite_mode=composite_mode,
                    location=(instruction_index,),
                    explicit_matrices=explicit_matrices,
                )
            )

        return SemanticCircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=pack_semantic_operations(operations),
            name=typed_circuit.name,
            metadata={"framework": self.framework_name},
        )

    def _convert_instruction(
        self,
        entry: object,
        qubit_ids: dict[object, str],
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
        *,
        composite_mode: str,
        location: tuple[int, ...] = (),
        explicit_matrices: bool = True,
    ) -> list[SemanticOperationIR]:
        operation, qubits, clbits = self._normalize_entry(entry)
        raw_name = str(getattr(operation, "name", operation.__class__.__name__))
        name = raw_name.lower()
        target_wires = tuple(qubit_ids[qubit] for qubit in qubits)
        parameters = tuple(getattr(operation, "params", ()) or ())
        matrix_metadata = self._matrix_metadata(
            operation,
            explicit_matrices=explicit_matrices,
        )

        if name == "measure":
            if not target_wires:
                raise UnsupportedOperationError(
                    "Qiskit instruction 'measure' has no quantum target"
                )
            if not clbits:
                raise UnsupportedOperationError(
                    "Qiskit instruction 'measure' has no classical target"
                )
            classical_target, classical_bit_label = classical_targets[clbits[0]]
            return [
                SemanticOperationIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=(target_wires[0],),
                    classical_target=classical_target,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=raw_name,
                        native_kind="measurement",
                        location=location,
                    ),
                    metadata={
                        "classical_bit_label": classical_bit_label,
                        **matrix_metadata,
                    },
                )
            ]
        if name == "if_else":
            return self._convert_if_else(
                operation=operation,
                qubits=qubits,
                clbits=clbits,
                qubit_ids=qubit_ids,
                classical_targets=classical_targets,
                register_targets=register_targets,
                composite_mode=composite_mode,
                location=location,
                explicit_matrices=explicit_matrices,
            )
        if name in {"switch_case", "for_loop", "while_loop"}:
            return self._convert_compact_control_flow(
                operation=operation,
                name=name,
                qubits=qubits,
                qubit_ids=qubit_ids,
                classical_targets=classical_targets,
                register_targets=register_targets,
                location=location,
            )
        if name == "barrier":
            return [
                SemanticOperationIR(
                    kind=OperationKind.BARRIER,
                    name="BARRIER",
                    target_wires=target_wires,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=raw_name,
                        native_kind="barrier",
                        location=location,
                    ),
                )
            ]
        if name == "swap":
            return [
                SemanticOperationIR(
                    kind=OperationKind.SWAP,
                    name="SWAP",
                    target_wires=target_wires,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=raw_name,
                        native_kind="swap",
                        location=location,
                    ),
                    metadata=matrix_metadata,
                )
            ]

        control_count = int(getattr(operation, "num_ctrl_qubits", 0) or 0)
        if control_count > 0 and len(target_wires) > control_count:
            base_gate = getattr(operation, "base_gate", None)
            base_name = getattr(base_gate, "name", None) or name.removeprefix("c")
            canonical_gate = canonical_gate_spec(str(base_name))
            return [
                SemanticOperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=canonical_gate.label,
                    canonical_family=canonical_gate.family,
                    target_wires=target_wires[control_count:],
                    control_wires=target_wires[:control_count],
                    parameters=parameters,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=raw_name,
                        native_kind="controlled_gate",
                        location=location,
                    ),
                    metadata=matrix_metadata,
                )
            ]

        if self._is_composite_instruction(operation):
            if composite_mode == "expand":
                return self._expand_definition(
                    operation=operation,
                    qubits=qubits,
                    clbits=clbits,
                    qubit_ids=qubit_ids,
                    classical_targets=classical_targets,
                    composite_mode=composite_mode,
                    location=location,
                    explicit_matrices=explicit_matrices,
                )
            if not target_wires:
                raise UnsupportedOperationError(
                    f"Qiskit operation '{raw_name}' has no drawable targets"
                )
            return [
                SemanticOperationIR(
                    kind=OperationKind.GATE,
                    name=raw_name,
                    label=raw_name,
                    target_wires=target_wires,
                    parameters=parameters,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=raw_name,
                        native_kind="composite",
                        composite_label=raw_name,
                        location=location,
                    ),
                    metadata=matrix_metadata,
                )
            ]

        if not target_wires:
            raise UnsupportedOperationError(f"Qiskit operation '{name}' has no drawable targets")
        canonical_gate = canonical_gate_spec(name)
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=target_wires,
                parameters=parameters,
                provenance=semantic_provenance(
                    framework=self.framework_name,
                    native_name=raw_name,
                    native_kind="gate",
                    location=location,
                ),
                metadata=matrix_metadata,
            )
        ]

    def _matrix_metadata(
        self,
        operation: object,
        *,
        explicit_matrices: bool = True,
    ) -> dict[str, object]:
        if not explicit_matrices:
            return {}

        matrix_getter = getattr(operation, "to_matrix", None)
        if not callable(matrix_getter):
            return {}

        try:
            matrix = matrix_getter()
        except Exception as exc:
            if not is_expected_matrix_unavailable_error(exc):
                raise
            return {}

        if square_matrix(matrix) is None:
            return {}
        return {"matrix": matrix}

    def _convert_if_else(
        self,
        *,
        operation: object,
        qubits: tuple[object, ...],
        clbits: tuple[object, ...],
        qubit_ids: dict[object, str],
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
        composite_mode: str,
        location: tuple[int, ...] = (),
        explicit_matrices: bool = True,
    ) -> list[SemanticOperationIR]:
        blocks = tuple(getattr(operation, "blocks", ()) or ())
        if not blocks:
            return []

        if len(blocks) > 1 and blocks[1] is not None:
            return self._convert_compact_control_flow(
                operation=operation,
                name="if_else",
                qubits=qubits,
                qubit_ids=qubit_ids,
                classical_targets=classical_targets,
                register_targets=register_targets,
                location=location,
            )

        condition = self._condition_from_qiskit(
            getattr(operation, "condition", None),
            classical_targets,
            register_targets,
        )
        true_block = blocks[0]
        if len(true_block.qubits) != len(qubits):
            raise UnsupportedOperationError(
                "Qiskit if_else true_block qubit mapping mismatch: "
                f"expected {len(true_block.qubits)} inner qubits, received {len(qubits)} outer qubits"
            )
        if len(true_block.clbits) != len(clbits):
            raise UnsupportedOperationError(
                "Qiskit if_else true_block clbit mapping mismatch: "
                f"expected {len(true_block.clbits)} inner clbits, received {len(clbits)} outer clbits"
            )
        nested_qubit_ids = {
            inner_qubit: qubit_ids[outer_qubit]
            for inner_qubit, outer_qubit in zip(true_block.qubits, qubits, strict=True)
        }
        nested_classical_targets = {
            inner_clbit: classical_targets[outer_clbit]
            for inner_clbit, outer_clbit in zip(true_block.clbits, clbits, strict=True)
            if outer_clbit in classical_targets
        }

        converted_operations: list[SemanticOperationIR] = []
        for nested_index, inner_entry in enumerate(true_block.data):
            converted_operations.extend(
                self._convert_instruction(
                    inner_entry,
                    nested_qubit_ids,
                    nested_classical_targets,
                    register_targets={},
                    composite_mode=composite_mode,
                    location=(*location, nested_index),
                    explicit_matrices=explicit_matrices,
                )
            )
        return [
            append_semantic_classical_conditions(node, (condition,))
            for node in converted_operations
        ]

    def _convert_compact_control_flow(
        self,
        *,
        operation: object,
        name: str,
        qubits: tuple[object, ...],
        qubit_ids: dict[object, str],
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
        location: tuple[int, ...],
    ) -> list[SemanticOperationIR]:
        target_wires = tuple(qubit_ids[qubit] for qubit in qubits)
        if not target_wires:
            raise UnsupportedOperationError(f"Qiskit control-flow '{name}' has no drawable targets")

        classical_conditions, condition_details = self._compact_control_flow_conditions(
            name=name,
            operation=operation,
            classical_targets=classical_targets,
            register_targets=register_targets,
        )
        hover_details = self._control_flow_hover_details(
            name=name,
            operation=operation,
            condition_details=condition_details,
        )
        label = self._CONTROL_FLOW_LABELS[name]
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name=label,
                label=label,
                target_wires=target_wires,
                classical_conditions=classical_conditions,
                hover_details=hover_details,
                provenance=semantic_provenance(
                    framework=self.framework_name,
                    native_name=name,
                    native_kind="control_flow",
                    location=location,
                ),
                metadata={"qiskit_control_flow": name},
            )
        ]

    def _compact_control_flow_conditions(
        self,
        *,
        name: str,
        operation: object,
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
    ) -> tuple[tuple[ClassicalConditionIR, ...], tuple[str, ...]]:
        if name in {"if_else", "while_loop"}:
            condition_source = getattr(operation, "condition", None)
            if condition_source is None:
                return (), ()
            try:
                condition = self._condition_from_qiskit(
                    condition_source,
                    classical_targets,
                    register_targets,
                )
            except UnsupportedOperationError:
                return (), normalized_detail_lines(
                    f"condition: {self._native_text(condition_source)}"
                )
            return (condition,), normalized_detail_lines(f"condition: {condition.expression}")

        if name == "switch_case":
            target_source = getattr(operation, "target", None)
            if target_source is None:
                return (), ()
            try:
                condition, target_text = self._switch_target_from_qiskit(
                    target_source,
                    classical_targets,
                    register_targets,
                )
            except UnsupportedOperationError:
                return (), normalized_detail_lines(f"target: {self._native_text(target_source)}")
            return (condition,), normalized_detail_lines(f"target: {target_text}")

        return (), ()

    def _control_flow_hover_details(
        self,
        *,
        name: str,
        operation: object,
        condition_details: Sequence[str],
    ) -> tuple[str, ...]:
        details: list[str] = [f"control flow: {name}", *condition_details]
        if name == "if_else":
            details.append("branches: true, false")
        elif name == "switch_case":
            case_summary = self._switch_case_summary(operation)
            if case_summary is not None:
                details.append(f"cases: {case_summary}")
        elif name == "for_loop":
            iteration_summary = self._for_loop_iteration_summary(operation)
            if iteration_summary is not None:
                details.append(f"iteration: {iteration_summary}")
        return normalized_detail_lines(*details)

    def _switch_case_summary(self, operation: object) -> str | None:
        values: tuple[object, ...] = ()
        cases_getter = getattr(operation, "cases", None)
        if callable(cases_getter):
            values = tuple(cases_getter())
        elif callable(getattr(operation, "cases_specifier", None)):
            values = tuple(
                case_value
                for case_value, _ in cast("object", operation).cases_specifier()  # type: ignore[attr-defined]
            )
        if not values:
            return None

        formatted_values = [self._switch_case_value_text(value) for value in values[:4]]
        if len(values) > 4:
            formatted_values.append("...")
        return ", ".join(formatted_values)

    def _switch_case_value_text(self, value: object) -> str:
        text = self._native_text(value)
        return "default" if text == "<default case>" else text

    def _for_loop_iteration_summary(self, operation: object) -> str | None:
        params = tuple(getattr(operation, "params", ()) or ())
        indexset = getattr(operation, "indexset", None)
        if indexset is None and params:
            indexset = params[0]
        loop_parameter = getattr(operation, "loop_parameter", None)
        if loop_parameter is None and len(params) > 1:
            loop_parameter = params[1]
        if indexset is None and loop_parameter is None:
            return None
        indexset_text = self._native_text(indexset) if indexset is not None else "unknown"
        if loop_parameter is None:
            return indexset_text
        return f"{self._native_text(loop_parameter)} in {indexset_text}"

    def _switch_target_from_qiskit(
        self,
        target: object,
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
    ) -> tuple[ClassicalConditionIR, str]:
        if self._is_known_classical_target(target, classical_targets):
            wire_id, bit_label = classical_targets[target]
            return ClassicalConditionIR(
                wire_ids=(wire_id,),
                expression=f"switch on {bit_label}",
            ), bit_label
        if self._is_known_classical_target(target, register_targets):
            wire_id, register_label = register_targets[target]
            return ClassicalConditionIR(
                wire_ids=(wire_id,),
                expression=f"switch on {register_label}",
            ), register_label
        raise UnsupportedOperationError("unsupported Qiskit switch target")

    def _condition_from_qiskit(
        self,
        condition: object,
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
    ) -> ClassicalConditionIR:
        if not isinstance(condition, tuple) or len(condition) != 2:
            raise UnsupportedOperationError("unsupported Qiskit classical condition shape")

        lhs, value = condition
        if self._is_known_classical_target(lhs, classical_targets):
            wire_id, bit_label = classical_targets[lhs]
            return ClassicalConditionIR(wire_ids=(wire_id,), expression=f"if {bit_label}={value}")
        if self._is_known_classical_target(lhs, register_targets):
            wire_id, register_label = register_targets[lhs]
            return ClassicalConditionIR(
                wire_ids=(wire_id,),
                expression=f"if {register_label}={value}",
            )
        raise UnsupportedOperationError("unsupported Qiskit classical condition target")

    def _is_known_classical_target(
        self,
        value: object,
        targets: Mapping[object, tuple[str, str]],
    ) -> bool:
        try:
            return value in targets
        except TypeError:
            return False

    def _native_text(self, value: object) -> str:
        if value is None:
            return "None"
        text = str(value).strip()
        if text:
            return text
        return value.__class__.__name__

    def _expand_definition(
        self,
        *,
        operation: object,
        qubits: tuple[object, ...],
        clbits: tuple[object, ...],
        qubit_ids: dict[object, str],
        classical_targets: dict[object, tuple[str, str]],
        composite_mode: str,
        location: tuple[int, ...] = (),
        explicit_matrices: bool = True,
    ) -> list[SemanticOperationIR]:
        definition = getattr(operation, "definition", None)
        if definition is None:
            return []

        if len(definition.qubits) != len(qubits):
            raise UnsupportedOperationError(
                "Qiskit composite definition qubit mapping mismatch: "
                f"expected {len(definition.qubits)} inner qubits, received {len(qubits)} outer qubits"
            )
        if len(definition.clbits) != len(clbits):
            raise UnsupportedOperationError(
                "Qiskit composite definition clbit mapping mismatch: "
                f"expected {len(definition.clbits)} inner clbits, received {len(clbits)} outer clbits"
            )

        nested_qubit_ids = {
            inner_qubit: qubit_ids[outer_qubit]
            for inner_qubit, outer_qubit in zip(definition.qubits, qubits, strict=True)
        }
        nested_classical_targets = {
            inner_clbit: classical_targets[outer_clbit]
            for inner_clbit, outer_clbit in zip(definition.clbits, clbits, strict=True)
            if outer_clbit in classical_targets
        }

        expanded_operations: list[SemanticOperationIR] = []
        for nested_index, inner_entry in enumerate(definition.data):
            expanded_operations.extend(
                self._convert_instruction(
                    inner_entry,
                    nested_qubit_ids,
                    nested_classical_targets,
                    register_targets={},
                    composite_mode=composite_mode,
                    location=(*location, nested_index),
                    explicit_matrices=explicit_matrices,
                )
            )
        return expanded_operations

    def _is_composite_instruction(self, operation: object) -> bool:
        definition = getattr(operation, "definition", None)
        if definition is None or not getattr(definition, "data", None):
            return False
        raw_name = str(getattr(operation, "name", operation.__class__.__name__))
        return canonical_gate_spec(raw_name).family.name == "CUSTOM"

    def _normalize_entry(
        self,
        entry: object,
    ) -> tuple[object, tuple[object, ...], tuple[object, ...]]:
        if hasattr(entry, "operation") and hasattr(entry, "qubits") and hasattr(entry, "clbits"):
            return entry.operation, tuple(entry.qubits), tuple(entry.clbits)
        if isinstance(entry, tuple) and len(entry) == 3:
            operation, qubits, clbits = entry
            return operation, tuple(qubits), tuple(clbits)
        raise UnsupportedOperationError(f"unsupported Qiskit instruction shape: {type(entry)!r}")

    def _build_classical_wires(
        self,
        circuit: _QiskitCircuitLike,
        clbits: list[object],
    ) -> tuple[list[WireIR], dict[object, tuple[str, str]], dict[object, tuple[str, str]]]:
        if not clbits:
            return [], {}, {}

        classical_wires: list[WireIR] = []
        classical_targets: dict[object, tuple[str, str]] = {}
        register_targets: dict[object, tuple[str, str]] = {}
        mapped_bits: set[object] = set()

        registers = tuple(getattr(circuit, "cregs", ()) or ())
        if registers:
            for index, register in enumerate(registers):
                wire_id = f"c{index}"
                label = getattr(register, "name", None) or wire_id
                bits = tuple(register)
                classical_wires.append(
                    WireIR(
                        id=wire_id,
                        index=index,
                        kind=WireKind.CLASSICAL,
                        label=label,
                        metadata={"bundle_size": len(bits)},
                    )
                )
                register_targets[register] = (wire_id, label)
                for bit_index, bit in enumerate(bits):
                    classical_targets[bit] = (wire_id, f"{label}[{bit_index}]")
                    mapped_bits.add(bit)

        unmapped_bits = [bit for bit in clbits if bit not in mapped_bits]
        if unmapped_bits:
            wire_id = f"c{len(classical_wires)}"
            classical_wires.append(
                WireIR(
                    id=wire_id,
                    index=len(classical_wires),
                    kind=WireKind.CLASSICAL,
                    label="c",
                    metadata={"bundle_size": len(unmapped_bits)},
                )
            )
            for bit_index, bit in enumerate(unmapped_bits):
                classical_targets[bit] = (wire_id, f"c[{bit_index}]")

        return classical_wires, classical_targets, register_targets
