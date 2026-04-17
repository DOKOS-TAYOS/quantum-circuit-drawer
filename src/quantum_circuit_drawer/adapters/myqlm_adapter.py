"""MyQLM adapter."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, cast

from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ..ir.circuit import CircuitIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ._helpers import (
    CanonicalGateSpec,
    append_classical_conditions,
    build_classical_register,
    canonical_gate_spec,
    expand_operation_sequence,
    extract_dependency_types,
    resolve_composite_mode,
    sequential_bit_labels,
)
from .base import BaseAdapter, OperationNode

_DEFAULT_OPERATION_TYPE_BY_INT: dict[int, str] = {
    0: "GATETYPE",
    1: "MEASURE",
    2: "RESET",
    3: "CLASSIC",
    4: "CLASSICCTRL",
    5: "BREAK",
    6: "REMAP",
}


def _build_operation_type_map() -> dict[int, str]:
    mapping = dict(_DEFAULT_OPERATION_TYPE_BY_INT)
    try:
        from qat.comm.datamodel.ttypes import OpType
    except (ImportError, ModuleNotFoundError):
        return mapping

    for name in ("GATETYPE", "MEASURE", "RESET", "CLASSIC", "CLASSICCTRL", "BREAK", "REMAP"):
        value = getattr(OpType, name, None)
        if isinstance(value, int):
            mapping[int(value)] = name
    return mapping


_OPERATION_TYPE_BY_INT = _build_operation_type_map()


class _MyQLMSyntaxLike(Protocol):
    name: str
    parameters: Sequence[object]


class _MyQLMOpLike(Protocol):
    gate: str | None
    qbits: Sequence[int]
    type: object
    cbits: Sequence[int] | None
    formula: str | None
    remap: Sequence[int] | None


class _MyQLMCircuitImplementationLike(Protocol):
    ops: Sequence[_MyQLMOpLike]
    ancillas: int
    nbqbits: int


class _MyQLMGateDefinitionLike(Protocol):
    name: str
    arity: int
    syntax: _MyQLMSyntaxLike | None
    nbctrls: int | None
    subgate: str | None
    circuit_implementation: _MyQLMCircuitImplementationLike | None


class _MyQLMCircuitLike(Protocol):
    ops: Sequence[_MyQLMOpLike]
    gateDic: Mapping[str, _MyQLMGateDefinitionLike]
    nbqbits: int
    nbcbits: int
    name: str | None


class MyQLMAdapter(BaseAdapter):
    """Convert ``qat.core.Circuit`` objects into CircuitIR."""

    framework_name = "myqlm"

    @classmethod
    def can_handle(cls, circuit: object) -> bool:
        circuit_types = extract_dependency_types("qat", ("core.Circuit",))
        return bool(circuit_types) and isinstance(circuit, circuit_types)

    def to_ir(self, circuit: object, options: Mapping[str, object] | None = None) -> CircuitIR:
        if not self.can_handle(circuit):
            raise TypeError("MyQLMAdapter received a non-MyQLM circuit")

        typed_circuit = cast(_MyQLMCircuitLike, circuit)
        composite_mode = resolve_composite_mode(options)
        quantum_count = max(
            self._declared_quantum_count(typed_circuit), self._used_qubit_count(circuit)
        )
        classical_count = max(
            self._declared_classical_count(typed_circuit),
            self._used_classical_count(circuit),
        )
        qubit_wire_ids = {index: f"q{index}" for index in range(quantum_count)}
        quantum_wires = [
            WireIR(
                id=qubit_wire_ids[index],
                index=index,
                kind=WireKind.QUANTUM,
                label=f"q{index}",
            )
            for index in range(quantum_count)
        ]
        classical_wires, classical_bit_targets = build_classical_register(
            sequential_bit_labels(classical_count)
        )
        classical_targets = {index: target for index, target in enumerate(classical_bit_targets)}

        operations = expand_operation_sequence(
            typed_circuit.ops,
            lambda operation: self._convert_operation(
                operation,
                gate_definitions=typed_circuit.gateDic,
                qubit_wire_ids=qubit_wire_ids,
                classical_targets=classical_targets,
                composite_mode=composite_mode,
            ),
        )

        return CircuitIR(
            quantum_wires=quantum_wires,
            classical_wires=classical_wires,
            layers=self.pack_operations(operations),
            name=typed_circuit.name,
            metadata={"framework": self.framework_name},
        )

    def _declared_quantum_count(self, circuit: _MyQLMCircuitLike) -> int:
        return max(int(circuit.nbqbits), 0)

    def _declared_classical_count(self, circuit: _MyQLMCircuitLike) -> int:
        return max(int(circuit.nbcbits), 0)

    def _used_qubit_count(self, circuit: object) -> int:
        operations = tuple(getattr(circuit, "ops", ()) or ())
        max_index = max(
            (max(getattr(operation, "qbits", ()) or (), default=-1) for operation in operations),
            default=-1,
        )
        return max_index + 1

    def _used_classical_count(self, circuit: object) -> int:
        operations = tuple(getattr(circuit, "ops", ()) or ())
        max_index = max(
            (max(getattr(operation, "cbits", ()) or (), default=-1) for operation in operations),
            default=-1,
        )
        return max_index + 1

    def _convert_operation(
        self,
        operation: _MyQLMOpLike,
        *,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        qubit_wire_ids: Mapping[int, str],
        classical_targets: Mapping[int, tuple[str, str]],
        composite_mode: str,
    ) -> list[OperationNode]:
        operation_type = self._operation_type_name(operation.type)
        if operation_type == "GATETYPE":
            return self._convert_gate_application(
                operation,
                gate_definitions=gate_definitions,
                qubit_wire_ids=qubit_wire_ids,
                composite_mode=composite_mode,
            )
        if operation_type == "CLASSICCTRL":
            converted = self._convert_gate_application(
                operation,
                gate_definitions=gate_definitions,
                qubit_wire_ids=qubit_wire_ids,
                composite_mode=composite_mode,
            )
            condition = self._classical_condition_for_operation(operation, classical_targets)
            return [append_classical_conditions(node, (condition,)) for node in converted]
        if operation_type == "MEASURE":
            return self._convert_measurement(operation, qubit_wire_ids, classical_targets)
        if operation_type == "RESET":
            return self._convert_reset(operation, qubit_wire_ids)
        if operation_type in {"BREAK", "CLASSIC", "REMAP"}:
            raise UnsupportedOperationError(
                f"unsupported myQLM operation type '{operation_type.lower()}'"
            )
        raise UnsupportedOperationError(
            f"unsupported myQLM operation type '{operation_type.lower()}'"
        )

    def _convert_gate_application(
        self,
        operation: _MyQLMOpLike,
        *,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        qubit_wire_ids: Mapping[int, str],
        composite_mode: str,
    ) -> list[OperationNode]:
        gate_key = operation.gate
        if gate_key is None:
            raise UnsupportedOperationError("myQLM gate operation is missing a gate definition")

        target_wires = self._target_wire_ids(operation.qbits, qubit_wire_ids)
        definition = gate_definitions.get(gate_key)
        display_name = self._gate_display_name(definition, gate_key)
        parameters = self._gate_parameters(definition)

        if definition is not None and definition.circuit_implementation is not None:
            if composite_mode == "expand":
                return self._expand_circuit_implementation(
                    definition.circuit_implementation,
                    gate_definitions=gate_definitions,
                    qubit_wire_ids=target_wires,
                    classical_targets={},
                    composite_mode=composite_mode,
                )
            return [
                OperationIR(
                    kind=OperationKind.GATE,
                    name=display_name,
                    label=display_name,
                    target_wires=tuple(target_wires.values()),
                    parameters=parameters,
                )
            ]

        control_count = self._control_count(definition)
        if control_count > 0:
            ordered_wires = tuple(target_wires.values())
            if len(ordered_wires) <= control_count:
                raise UnsupportedOperationError(
                    f"myQLM controlled gate '{display_name}' has no target wires after controls"
                )
            base_gate_spec = self._subgate_spec(definition, gate_definitions)
            return [
                OperationIR(
                    kind=OperationKind.CONTROLLED_GATE,
                    name=base_gate_spec.label,
                    canonical_family=base_gate_spec.family,
                    target_wires=ordered_wires[control_count:],
                    control_wires=ordered_wires[:control_count],
                    parameters=parameters,
                )
            ]

        canonical_gate = canonical_gate_spec(display_name)
        ordered_wires = tuple(target_wires.values())
        if canonical_gate.label == "SWAP":
            return [OperationIR(kind=OperationKind.SWAP, name="SWAP", target_wires=ordered_wires)]
        return [
            OperationIR(
                kind=OperationKind.GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=ordered_wires,
                parameters=parameters,
            )
        ]

    def _expand_circuit_implementation(
        self,
        implementation: _MyQLMCircuitImplementationLike,
        *,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        qubit_wire_ids: Mapping[int, str],
        classical_targets: Mapping[int, tuple[str, str]],
        composite_mode: str,
    ) -> list[OperationNode]:
        ancilla_count = int(getattr(implementation, "ancillas", 0) or 0)
        required_qubits = int(getattr(implementation, "nbqbits", len(qubit_wire_ids)) or 0)
        if ancilla_count > 0:
            raise UnsupportedOperationError(
                "myQLM composite operations with ancillas are not supported yet"
            )
        if required_qubits > len(qubit_wire_ids):
            raise UnsupportedOperationError(
                "myQLM composite operation requires more qubits than the enclosing call provides"
            )

        nested_wire_ids = {index: qubit_wire_ids[index] for index in range(required_qubits)}
        return expand_operation_sequence(
            implementation.ops,
            lambda nested_operation: self._convert_operation(
                nested_operation,
                gate_definitions=gate_definitions,
                qubit_wire_ids=nested_wire_ids,
                classical_targets=classical_targets,
                composite_mode=composite_mode,
            ),
        )

    def _convert_measurement(
        self,
        operation: _MyQLMOpLike,
        qubit_wire_ids: Mapping[int, str],
        classical_targets: Mapping[int, tuple[str, str]],
    ) -> list[OperationNode]:
        qubits = tuple(operation.qbits)
        classical_bits = tuple(operation.cbits or ())
        if len(qubits) != len(classical_bits):
            raise UnsupportedOperationError("myQLM measurement expects matching qubit/cbit counts")

        converted_measurements: list[OperationNode] = []
        for qubit_index, cbit_index in zip(qubits, classical_bits, strict=True):
            classical_target, bit_label = self._classical_target(cbit_index, classical_targets)
            converted_measurements.append(
                MeasurementIR(
                    kind=OperationKind.MEASUREMENT,
                    name="M",
                    target_wires=(self._wire_id_for_index(qubit_index, qubit_wire_ids),),
                    classical_target=classical_target,
                    metadata={"classical_bit_label": bit_label},
                )
            )
        return converted_measurements

    def _convert_reset(
        self,
        operation: _MyQLMOpLike,
        qubit_wire_ids: Mapping[int, str],
    ) -> list[OperationIR]:
        if operation.formula is not None or tuple(operation.cbits or ()):
            raise UnsupportedOperationError("myQLM classical resets are not supported yet")
        qubits = tuple(operation.qbits)
        if not qubits:
            raise UnsupportedOperationError("myQLM reset operation does not reference any qubits")

        return [
            OperationIR(
                kind=OperationKind.GATE,
                name="RESET",
                target_wires=(self._wire_id_for_index(qubit_index, qubit_wire_ids),),
            )
            for qubit_index in qubits
        ]

    def _classical_condition_for_operation(
        self,
        operation: _MyQLMOpLike,
        classical_targets: Mapping[int, tuple[str, str]],
    ) -> ClassicalConditionIR:
        classical_bits = tuple(operation.cbits or ())
        if operation.formula is not None or len(classical_bits) != 1:
            raise UnsupportedOperationError(
                "myQLM classical control only supports a single control bit without formulas"
            )

        wire_id, bit_label = self._classical_target(classical_bits[0], classical_targets)
        return ClassicalConditionIR(wire_ids=(wire_id,), expression=f"if {bit_label}=1")

    def _operation_type_name(self, raw_type: object) -> str:
        if hasattr(raw_type, "name"):
            return str(getattr(raw_type, "name")).upper()
        if isinstance(raw_type, str):
            return raw_type.upper()
        if isinstance(raw_type, int):
            return _OPERATION_TYPE_BY_INT.get(raw_type, str(raw_type)).upper()
        return str(raw_type).upper()

    def _gate_display_name(
        self,
        definition: _MyQLMGateDefinitionLike | None,
        gate_key: str,
    ) -> str:
        if definition is not None and definition.syntax is not None and definition.syntax.name:
            return str(definition.syntax.name)
        if definition is not None and definition.name:
            return str(definition.name)
        return gate_key

    def _gate_parameters(
        self,
        definition: _MyQLMGateDefinitionLike | None,
    ) -> tuple[object, ...]:
        if definition is None or definition.syntax is None:
            return ()
        return tuple(
            self._normalize_parameter_value(parameter)
            for parameter in (definition.syntax.parameters or ())
        )

    def _normalize_parameter_value(self, parameter: object) -> object:
        if isinstance(parameter, bool | int | float | complex | str):
            return parameter

        int_value = getattr(parameter, "int_p", None)
        if int_value is not None:
            return int(int_value)

        double_value = getattr(parameter, "double_p", None)
        if double_value is not None:
            return float(double_value)

        string_value = getattr(parameter, "string_p", None)
        if isinstance(string_value, str) and string_value:
            return string_value

        complex_value = self._complex_parameter_value(getattr(parameter, "complex_p", None))
        if complex_value is not None:
            return complex_value

        return parameter

    def _complex_parameter_value(self, value: object) -> complex | None:
        if value is None:
            return None

        real_part = getattr(value, "re", getattr(value, "real", None))
        imaginary_part = getattr(value, "im", getattr(value, "imag", None))
        if isinstance(real_part, int | float) and isinstance(imaginary_part, int | float):
            return complex(float(real_part), float(imaginary_part))
        return None

    def _control_count(self, definition: _MyQLMGateDefinitionLike | None) -> int:
        if definition is None:
            return 0
        control_count = getattr(definition, "nbctrls", None)
        if control_count is None:
            return 0
        return int(control_count)

    def _subgate_spec(
        self,
        definition: _MyQLMGateDefinitionLike | None,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
    ) -> CanonicalGateSpec:
        if definition is None or definition.subgate is None:
            raise UnsupportedOperationError("myQLM controlled gate is missing its subgate")
        return self._resolve_gate_spec(str(definition.subgate), gate_definitions, seen=set())

    def _resolve_gate_spec(
        self,
        gate_key: str,
        gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
        *,
        seen: set[str],
    ) -> CanonicalGateSpec:
        if gate_key in seen:
            raise UnsupportedOperationError(
                f"myQLM gate definition cycle detected for '{gate_key}'"
            )
        seen.add(gate_key)
        definition = gate_definitions.get(gate_key)
        if definition is None:
            return canonical_gate_spec(gate_key)
        if definition.subgate is not None and self._control_count(definition) > 0:
            return self._resolve_gate_spec(str(definition.subgate), gate_definitions, seen=seen)
        return canonical_gate_spec(self._gate_display_name(definition, gate_key))

    def _target_wire_ids(
        self,
        qubit_indexes: Sequence[int],
        qubit_wire_ids: Mapping[int, str],
    ) -> dict[int, str]:
        return {
            position: self._wire_id_for_index(qubit_index, qubit_wire_ids)
            for position, qubit_index in enumerate(qubit_indexes)
        }

    def _wire_id_for_index(self, qubit_index: int, qubit_wire_ids: Mapping[int, str]) -> str:
        try:
            return qubit_wire_ids[int(qubit_index)]
        except KeyError as exc:
            raise UnsupportedOperationError(
                f"myQLM operation references unknown qubit index {qubit_index}"
            ) from exc

    def _classical_target(
        self,
        classical_index: int,
        classical_targets: Mapping[int, tuple[str, str]],
    ) -> tuple[str, str]:
        try:
            return classical_targets[int(classical_index)]
        except KeyError as exc:
            raise UnsupportedOperationError(
                f"myQLM operation references unknown classical bit index {classical_index}"
            ) from exc
