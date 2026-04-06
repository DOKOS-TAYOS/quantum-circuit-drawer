"""Qiskit adapter."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from typing import Protocol, cast

from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ._helpers import canonical_gate_spec, extract_dependency_types
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
        if not self.can_handle(circuit):
            raise TypeError("QiskitAdapter received a non-Qiskit circuit")

        typed_circuit = cast(_QiskitCircuitLike, circuit)
        composite_mode = self._composite_mode(options)
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

        operations: list[OperationIR | MeasurementIR] = []
        for entry in typed_circuit.data:
            operations.extend(
                self._convert_instruction(
                    entry,
                    qubit_ids,
                    classical_targets,
                    register_targets,
                    composite_mode=composite_mode,
                )
            )

        layers = self.pack_operations(operations)
        return CircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=layers,
            name=typed_circuit.name,
            metadata={"framework": self.framework_name},
        )

    def _composite_mode(self, options: Mapping[str, object] | None) -> str:
        requested_mode = options.get("composite_mode") if options is not None else None
        return str(requested_mode) if requested_mode is not None else "compact"

    def _convert_instruction(
        self,
        entry: object,
        qubit_ids: dict[object, str],
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
        *,
        composite_mode: str,
    ) -> list[OperationIR | MeasurementIR]:
        operation, qubits, clbits = self._normalize_entry(entry)
        raw_name = str(getattr(operation, "name", operation.__class__.__name__))
        name = raw_name.lower()
        target_wires = tuple(qubit_ids[qubit] for qubit in qubits)
        parameters = tuple(getattr(operation, "params", ()) or ())

        if name == "measure":
            classical_target, classical_bit_label = classical_targets[clbits[0]]
            return [
                MeasurementIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=(target_wires[0],),
                    classical_target=classical_target,
                    metadata={"classical_bit_label": classical_bit_label},
                )
            ]
        if hasattr(operation, "blocks") and hasattr(operation, "condition"):
            return self._convert_if_else(
                operation=operation,
                qubits=qubits,
                clbits=clbits,
                qubit_ids=qubit_ids,
                classical_targets=classical_targets,
                register_targets=register_targets,
                composite_mode=composite_mode,
            )
        if name == "barrier":
            return [
                OperationIR(
                    kind=OperationKind.BARRIER,
                    name="BARRIER",
                    target_wires=target_wires,
                )
            ]
        if name == "swap":
            return [OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=target_wires)]

        control_count = int(getattr(operation, "num_ctrl_qubits", 0) or 0)
        if control_count > 0 and len(target_wires) > control_count:
            base_gate = getattr(operation, "base_gate", None)
            base_name = getattr(base_gate, "name", None) or name.removeprefix("c")
            canonical_gate = canonical_gate_spec(str(base_name))
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=canonical_gate.label,
                    canonical_family=canonical_gate.family,
                    target_wires=target_wires[control_count:],
                    control_wires=target_wires[:control_count],
                    parameters=parameters,
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
                )
            if not target_wires:
                raise UnsupportedOperationError(
                    f"Qiskit operation '{raw_name}' has no drawable targets"
                )
            return [
                OperationIR(
                    kind=OperationKind.GATE,
                    name=raw_name,
                    label=raw_name,
                    target_wires=target_wires,
                    parameters=parameters,
                )
            ]

        if not target_wires:
            raise UnsupportedOperationError(f"Qiskit operation '{name}' has no drawable targets")
        canonical_gate = canonical_gate_spec(name)
        return [
            OperationIR(
                kind=OperationKind.GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=target_wires,
                parameters=parameters,
            )
        ]

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
    ) -> list[OperationIR | MeasurementIR]:
        blocks = tuple(getattr(operation, "blocks", ()) or ())
        if not blocks:
            return []

        if len(blocks) > 1 and blocks[1] is not None:
            target_wires = tuple(qubit_ids[qubit] for qubit in qubits)
            return [
                OperationIR(
                    kind=OperationKind.GATE,
                    name="IF/ELSE",
                    label="IF/ELSE",
                    target_wires=target_wires,
                )
            ]

        condition = self._condition_from_qiskit(
            getattr(operation, "condition", None),
            classical_targets,
            register_targets,
        )
        true_block = blocks[0]
        nested_qubit_ids = {
            inner_qubit: qubit_ids[outer_qubit]
            for inner_qubit, outer_qubit in zip(true_block.qubits, qubits, strict=False)
        }
        nested_classical_targets = {
            inner_clbit: classical_targets[outer_clbit]
            for inner_clbit, outer_clbit in zip(true_block.clbits, clbits, strict=False)
            if outer_clbit in classical_targets
        }

        converted_operations: list[OperationIR | MeasurementIR] = []
        for inner_entry in true_block.data:
            converted_operations.extend(
                self._convert_instruction(
                    inner_entry,
                    nested_qubit_ids,
                    nested_classical_targets,
                    register_targets={},
                    composite_mode=composite_mode,
                )
            )
        return [self._append_classical_condition(node, condition) for node in converted_operations]

    def _condition_from_qiskit(
        self,
        condition: object,
        classical_targets: dict[object, tuple[str, str]],
        register_targets: dict[object, tuple[str, str]],
    ) -> ClassicalConditionIR:
        if not isinstance(condition, tuple) or len(condition) != 2:
            raise UnsupportedOperationError("unsupported Qiskit classical condition shape")

        lhs, value = condition
        if lhs in classical_targets:
            wire_id, bit_label = classical_targets[lhs]
            return ClassicalConditionIR(wire_ids=(wire_id,), expression=f"if {bit_label}={value}")
        if lhs in register_targets:
            wire_id, register_label = register_targets[lhs]
            return ClassicalConditionIR(
                wire_ids=(wire_id,),
                expression=f"if {register_label}={value}",
            )
        raise UnsupportedOperationError("unsupported Qiskit classical condition target")

    def _append_classical_condition(
        self,
        operation: OperationIR | MeasurementIR,
        condition: ClassicalConditionIR,
    ) -> OperationIR | MeasurementIR:
        return replace(
            operation,
            classical_conditions=(*operation.classical_conditions, condition),
        )

    def _expand_definition(
        self,
        *,
        operation: object,
        qubits: tuple[object, ...],
        clbits: tuple[object, ...],
        qubit_ids: dict[object, str],
        classical_targets: dict[object, tuple[str, str]],
        composite_mode: str,
    ) -> list[OperationIR | MeasurementIR]:
        definition = getattr(operation, "definition", None)
        if definition is None:
            return []

        nested_qubit_ids = {
            inner_qubit: qubit_ids[outer_qubit]
            for inner_qubit, outer_qubit in zip(definition.qubits, qubits, strict=False)
        }
        nested_classical_targets = {
            inner_clbit: classical_targets[outer_clbit]
            for inner_clbit, outer_clbit in zip(definition.clbits, clbits, strict=False)
            if outer_clbit in classical_targets
        }

        converted_operations: list[OperationIR | MeasurementIR] = []
        for inner_entry in definition.data:
            converted_operations.extend(
                self._convert_instruction(
                    inner_entry,
                    nested_qubit_ids,
                    nested_classical_targets,
                    register_targets={},
                    composite_mode=composite_mode,
                )
            )
        return converted_operations

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
        elif not classical_wires:
            classical_wires.append(
                WireIR(
                    id="c0",
                    index=0,
                    kind=WireKind.CLASSICAL,
                    label="c",
                    metadata={"bundle_size": len(clbits)},
                )
            )
            for bit_index, bit in enumerate(clbits):
                classical_targets[bit] = ("c0", f"c[{bit_index}]")
            for register in registers:
                register_targets[register] = ("c0", getattr(register, "name", None) or "c")

        return classical_wires, classical_targets, register_targets
