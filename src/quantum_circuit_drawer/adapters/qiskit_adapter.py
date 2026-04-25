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
from . import _qiskit_classical as qiskit_classical_helpers
from . import _qiskit_control_flow as qiskit_control_flow_helpers
from ._fundamental_decompositions import expand_fundamental_semantic_gate
from ._helpers import (
    canonical_gate_spec,
    extract_dependency_types,
    is_expected_matrix_unavailable_error,
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
        decomposition_origin: str | None = None,
        composite_label: str | None = None,
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
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
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
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
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
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
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
                    control_values=self._control_values_from_qiskit(
                        operation,
                        control_count=control_count,
                    ),
                    parameters=parameters,
                    provenance=semantic_provenance(
                        framework=self.framework_name,
                        native_name=raw_name,
                        native_kind="controlled_gate",
                        decomposition_origin=decomposition_origin,
                        composite_label=composite_label,
                        location=location,
                    ),
                    metadata=matrix_metadata,
                )
            ]

        canonical_gate = canonical_gate_spec(name)
        if composite_mode == "expand":
            expanded_fundamental = expand_fundamental_semantic_gate(
                framework=self.framework_name,
                canonical_family=canonical_gate.family,
                raw_name=raw_name,
                target_wires=target_wires,
                parameters=parameters,
                location=location,
            )
            if expanded_fundamental:
                return list(expanded_fundamental)

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
                        decomposition_origin=decomposition_origin,
                        composite_label=raw_name,
                        location=location,
                    ),
                    metadata=matrix_metadata,
                )
            ]

        if not target_wires:
            raise UnsupportedOperationError(f"Qiskit operation '{name}' has no drawable targets")
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
                    decomposition_origin=decomposition_origin,
                    composite_label=composite_label,
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

    def _control_values_from_qiskit(
        self,
        operation: object,
        *,
        control_count: int,
    ) -> tuple[tuple[int, ...], ...]:
        if control_count <= 0:
            return ()
        ctrl_state = getattr(operation, "ctrl_state", None)
        if ctrl_state is None:
            return ()

        state_value = int(ctrl_state)
        state_bits = format(state_value, f"0{control_count}b")
        resolved = tuple((int(bit),) for bit in state_bits)
        if all(entry == (1,) for entry in resolved):
            return ()
        return resolved

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
        return qiskit_control_flow_helpers.convert_if_else(
            framework_name=self.framework_name,
            operation=operation,
            qubits=qubits,
            clbits=clbits,
            qubit_ids=qubit_ids,
            classical_targets=classical_targets,
            register_targets=register_targets,
            composite_mode=composite_mode,
            location=location,
            explicit_matrices=explicit_matrices,
            condition_from_qiskit=self._condition_from_qiskit,
            convert_compact_control_flow=self._convert_compact_control_flow,
            instruction_converter=self._convert_instruction,
        )

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
        label: str | None = None,
    ) -> list[SemanticOperationIR]:
        return qiskit_control_flow_helpers.convert_compact_control_flow(
            framework_name=self.framework_name,
            operation=operation,
            name=name,
            qubits=qubits,
            qubit_ids=qubit_ids,
            classical_targets=classical_targets,
            register_targets=register_targets,
            location=location,
            label=label,
            compact_control_flow_conditions=self._compact_control_flow_conditions,
            control_flow_hover_details=self._control_flow_hover_details,
        )

    def _compact_control_flow_conditions(
        self,
        *,
        name: str,
        operation: object,
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
    ) -> tuple[tuple[ClassicalConditionIR, ...], tuple[str, ...]]:
        return qiskit_control_flow_helpers.compact_control_flow_conditions(
            name=name,
            operation=operation,
            classical_targets=classical_targets,
            register_targets=register_targets,
            condition_from_qiskit=self._condition_from_qiskit,
            switch_target_from_qiskit=self._switch_target_from_qiskit,
            native_text=self._native_text,
        )

    def _control_flow_hover_details(
        self,
        *,
        name: str,
        operation: object,
        condition_details: Sequence[str],
    ) -> tuple[str, ...]:
        return qiskit_control_flow_helpers.control_flow_hover_details(
            name=name,
            operation=operation,
            condition_details=condition_details,
            native_text=self._native_text,
        )

    def _switch_target_from_qiskit(
        self,
        target: object,
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
    ) -> tuple[ClassicalConditionIR, str]:
        return qiskit_classical_helpers.switch_target_from_qiskit(
            target,
            classical_targets,
            register_targets,
        )

    def _condition_from_qiskit(
        self,
        condition: object,
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
    ) -> ClassicalConditionIR:
        return qiskit_classical_helpers.condition_from_qiskit(
            condition,
            classical_targets,
            register_targets,
        )

    def _native_text(self, value: object) -> str:
        return qiskit_classical_helpers.native_text(value)

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
        composite_name = str(getattr(operation, "name", operation.__class__.__name__))

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
                    decomposition_origin=composite_name,
                    composite_label=composite_name,
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
