"""Shared MyQLM adapter resolution helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Protocol

from ..config import UnsupportedPolicy
from ..exceptions import UnsupportedOperationError
from ..ir import ClassicalConditionIR
from ._helpers import CanonicalGateSpec, canonical_gate_spec

_DEFAULT_OPERATION_TYPE_BY_INT: dict[int, str] = {
    0: "GATETYPE",
    1: "MEASURE",
    2: "RESET",
    3: "CLASSIC",
    4: "CLASSICCTRL",
    5: "BREAK",
    6: "REMAP",
}

_CLASSICAL_BIT_REFERENCE_PATTERN = re.compile(r"c\[(\d+)\]")


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


def unsupported_policy_from_options(options: Mapping[str, object] | None) -> UnsupportedPolicy:
    if options is None:
        return UnsupportedPolicy.RAISE
    raw_policy = options.get("unsupported_policy", UnsupportedPolicy.RAISE)
    if isinstance(raw_policy, UnsupportedPolicy):
        return raw_policy
    try:
        return UnsupportedPolicy(str(raw_policy))
    except ValueError:
        return UnsupportedPolicy.RAISE


def declared_quantum_count(circuit: _MyQLMCircuitLike) -> int:
    return max(int(circuit.nbqbits), 0)


def declared_classical_count(circuit: _MyQLMCircuitLike) -> int:
    return max(int(circuit.nbcbits), 0)


def used_qubit_count(circuit: object) -> int:
    operations = tuple(getattr(circuit, "ops", ()) or ())
    max_index = max(
        (max(getattr(operation, "qbits", ()) or (), default=-1) for operation in operations),
        default=-1,
    )
    return max_index + 1


def used_classical_count(circuit: object) -> int:
    operations = tuple(getattr(circuit, "ops", ()) or ())
    max_index = max(
        (max(getattr(operation, "cbits", ()) or (), default=-1) for operation in operations),
        default=-1,
    )
    return max_index + 1


def operation_type_name(raw_type: object) -> str:
    if hasattr(raw_type, "name"):
        return str(getattr(raw_type, "name")).upper()
    if isinstance(raw_type, str):
        return raw_type.upper()
    if isinstance(raw_type, int):
        return _OPERATION_TYPE_BY_INT.get(raw_type, str(raw_type)).upper()
    return str(raw_type).upper()


def gate_display_name(
    definition: _MyQLMGateDefinitionLike | None,
    gate_key: str,
) -> str:
    if definition is not None and definition.syntax is not None and definition.syntax.name:
        return str(definition.syntax.name)
    if definition is not None and definition.name:
        return str(definition.name)
    return gate_key


def gate_parameters(
    definition: _MyQLMGateDefinitionLike | None,
) -> tuple[object, ...]:
    if definition is None or definition.syntax is None:
        return ()
    return tuple(
        normalize_parameter_value(parameter) for parameter in (definition.syntax.parameters or ())
    )


def normalize_parameter_value(parameter: object) -> object:
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

    complex_value = complex_parameter_value(getattr(parameter, "complex_p", None))
    if complex_value is not None:
        return complex_value

    return parameter


def complex_parameter_value(value: object) -> complex | None:
    if value is None:
        return None

    real_part = getattr(value, "re", getattr(value, "real", None))
    imaginary_part = getattr(value, "im", getattr(value, "imag", None))
    if isinstance(real_part, int | float) and isinstance(imaginary_part, int | float):
        return complex(float(real_part), float(imaginary_part))
    return None


def control_count(definition: _MyQLMGateDefinitionLike | None) -> int:
    if definition is None:
        return 0
    resolved_control_count = getattr(definition, "nbctrls", None)
    if resolved_control_count is None:
        return 0
    return int(resolved_control_count)


def subgate_spec(
    definition: _MyQLMGateDefinitionLike | None,
    gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
) -> CanonicalGateSpec:
    if definition is None or definition.subgate is None:
        raise UnsupportedOperationError("myQLM controlled gate is missing its subgate")
    return resolve_gate_spec(str(definition.subgate), gate_definitions, seen=set())


def resolve_gate_spec(
    gate_key: str,
    gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
    *,
    seen: set[str],
) -> CanonicalGateSpec:
    if gate_key in seen:
        raise UnsupportedOperationError(f"myQLM gate definition cycle detected for '{gate_key}'")
    seen.add(gate_key)
    definition = gate_definitions.get(gate_key)
    if definition is None:
        return canonical_gate_spec(gate_key)
    if definition.subgate is not None and control_count(definition) > 0:
        return resolve_gate_spec(str(definition.subgate), gate_definitions, seen=seen)
    return canonical_gate_spec(gate_display_name(definition, gate_key))


def target_wire_ids(
    qubit_indexes: Sequence[int],
    qubit_wire_ids: Mapping[int, str],
) -> dict[int, str]:
    return {
        position: wire_id_for_index(qubit_index, qubit_wire_ids)
        for position, qubit_index in enumerate(qubit_indexes)
    }


def wire_id_for_index(qubit_index: int, qubit_wire_ids: Mapping[int, str]) -> str:
    try:
        return qubit_wire_ids[int(qubit_index)]
    except KeyError as exc:
        raise UnsupportedOperationError(
            f"myQLM operation references unknown qubit index {qubit_index}"
        ) from exc


def classical_target(
    classical_index: int,
    classical_targets: Mapping[int, tuple[str, str]],
) -> tuple[str, str]:
    try:
        return classical_targets[int(classical_index)]
    except KeyError as exc:
        raise UnsupportedOperationError(
            f"myQLM operation references unknown classical bit index {classical_index}"
        ) from exc


def classical_condition_for_operation(
    operation: _MyQLMOpLike,
    classical_targets: Mapping[int, tuple[str, str]],
) -> ClassicalConditionIR:
    classical_bits = tuple(operation.cbits or ())
    if not classical_bits:
        raise UnsupportedOperationError(
            "myQLM classical control requires at least one classical control bit"
        )

    resolved_targets = tuple(
        classical_target(classical_index, classical_targets) for classical_index in classical_bits
    )
    wire_ids = tuple(wire_id for wire_id, _ in resolved_targets)
    bit_labels = tuple(bit_label for _, bit_label in resolved_targets)

    expression_text = (operation.formula or "").strip()
    if not expression_text:
        if len(bit_labels) == 1:
            expression_text = f"{bit_labels[0]}=1"
        else:
            expression_text = " && ".join(f"{bit_label}=1" for bit_label in bit_labels)
    if not expression_text.startswith("if "):
        expression_text = f"if {expression_text}"

    return ClassicalConditionIR(
        wire_ids=wire_ids,
        expression=expression_text,
        metadata={"classical_bits": bit_labels},
    )


def safe_classical_condition_for_operation(
    operation: _MyQLMOpLike,
    classical_targets: Mapping[int, tuple[str, str]],
) -> ClassicalConditionIR | None:
    formula_text = (operation.formula or "").strip()
    if formula_text and not formula_references_known_bits(formula_text, operation.cbits):
        return None
    try:
        return classical_condition_for_operation(operation, classical_targets)
    except UnsupportedOperationError:
        return None


def formula_references_known_bits(
    formula_text: str,
    classical_bits: Sequence[int] | None,
) -> bool:
    known_bits = {int(index) for index in (classical_bits or ())}
    referenced_bits = {
        int(match.group(1)) for match in _CLASSICAL_BIT_REFERENCE_PATTERN.finditer(formula_text)
    }
    return referenced_bits.issubset(known_bits)


def placeholder_target_wires(
    operation: _MyQLMOpLike,
    qubit_wire_ids: Mapping[int, str],
) -> tuple[str, ...]:
    qubit_indexes = tuple(operation.qbits)
    if not qubit_indexes:
        return ()
    return tuple(target_wire_ids(qubit_indexes, qubit_wire_ids).values())


def placeholder_display_name(
    operation: _MyQLMOpLike,
    *,
    operation_type: str,
    gate_definitions: Mapping[str, _MyQLMGateDefinitionLike],
) -> str:
    if operation.gate is not None:
        return gate_display_name(gate_definitions.get(operation.gate), operation.gate)
    return operation_type


def classical_box_target_wires(
    *,
    operation_type: str,
    resolved_targets: Sequence[tuple[str, str]],
) -> tuple[str, ...]:
    if operation_type == "CLASSIC":
        return (resolved_targets[0][0],)
    return tuple(dict.fromkeys(wire_id for wire_id, _ in resolved_targets))


def remap_summary(
    operation: _MyQLMOpLike,
    qubit_wire_ids: Mapping[int, str],
) -> str:
    qubits = tuple(int(index) for index in operation.qbits)
    remap_values = tuple(int(index) for index in (operation.remap or ()))
    if remap_values and len(remap_values) == len(qubits):
        try:
            mappings = ", ".join(
                f"{wire_id_for_index(source_index, qubit_wire_ids)}->"
                f"{wire_id_for_index(target_index, qubit_wire_ids)}"
                for source_index, target_index in zip(qubits, remap_values, strict=True)
            )
        except UnsupportedOperationError:
            pass
        else:
            return f"remap: {mappings}"
    return f"remap raw: qbits={qubits}, remap={remap_values}"
