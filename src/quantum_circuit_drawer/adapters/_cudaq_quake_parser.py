"""Private Quake/MLIR parser used by the CUDA-Q adapter."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..exceptions import UnsupportedOperationError
from ..ir.measurements import MeasurementIR
from ..ir.operations import OperationIR, OperationKind
from ..ir.wires import WireIR, WireKind
from ..utils.formatting import format_gate_name
from .base import OperationNode

_ASSIGNMENT_RE = re.compile(r"^(?:(?P<result>%[\w$.]+)\s*=\s*)?(?P<body>.+)$")
_CONSTANT_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*arith\.constant\s+(?P<value>[^:]+)\s*:\s*(?P<type>\S+)$"
)
_CAST_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*arith\.(?:extsi|index_cast|trunci|sitofp|fptosi|extf|truncf)\s+"
    r"(?P<source>%[\w$.]+)\s*:\s*.+$"
)
_VECTOR_ALLOCA_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*quake\.alloca(?:\((?P<size_arg>[^)]*)\))?"
    r"\s*:\s*!quake\.(?:veq|qvec)<(?P<arity>[^>]+)>$"
)
_SCALAR_ALLOCA_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*quake\.alloca(?:\([^)]*\))?\s*:\s*!quake\.(?:ref|qref)$"
)
_EXTRACT_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*quake\.(?:extract_ref|qextract)\s+"
    r"(?P<vector>%[\w$.]+)\[(?P<index>[^\]]+)\].*$"
)
_UNWRAP_RE = re.compile(r"^(?P<result>%[\w$.]+)\s*=\s*quake\.unwrap\s+(?P<source>%[\w$.]+).*$")
_WRAP_RE = re.compile(r"^quake\.wrap\s+(?P<wire>%[\w$.]+)\s+to\s+(?P<target>%[\w$.]+).*$")
_SSA_TOKEN_RE = re.compile(r"%[\w$.]+")
_NUMBER_TOKEN_RE = re.compile(r"[-+]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:e[-+]?\d+)?")


@dataclass(slots=True)
class CudaqQuakeParser:
    mlir: str
    quantum_wires: list[WireIR] = field(default_factory=list)
    measurement_count: int = 0
    _next_wire_index: int = 0
    _vector_aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    _ref_aliases: dict[str, str] = field(default_factory=dict)
    _wire_aliases: dict[str, str] = field(default_factory=dict)
    _numeric_aliases: dict[str, int | float] = field(default_factory=dict)

    def parse(self) -> tuple[list[WireIR], list[OperationNode]]:
        operations: list[OperationNode] = []
        for raw_line in self.mlir.splitlines():
            line = raw_line.strip()
            if not line or line in {"module {", "}", "return"}:
                continue
            if line.startswith(("func.func", "cc.scope", "attributes", "module attributes")):
                continue
            if line in {"{", "}"} or line.endswith("{"):
                self._reject_control_flow(line)
                continue
            if self._parse_numeric_alias(line):
                continue
            if self._parse_vector_alloca(line):
                continue
            if self._parse_scalar_alloca(line):
                continue
            if self._parse_extract(line):
                continue
            if self._parse_unwrap(line):
                continue
            if self._parse_wrap(line):
                continue
            operations.extend(self._parse_operation(line))
        return self.quantum_wires, operations

    def _parse_numeric_alias(self, line: str) -> bool:
        constant_match = _CONSTANT_RE.match(line)
        if constant_match is not None:
            value = self._parse_numeric_literal(constant_match.group("value").strip())
            if value is not None:
                self._numeric_aliases[constant_match.group("result")] = value
            return True
        cast_match = _CAST_RE.match(line)
        if cast_match is not None:
            source = cast_match.group("source")
            if source in self._numeric_aliases:
                self._numeric_aliases[cast_match.group("result")] = self._numeric_aliases[source]
            return True
        return False

    def _parse_vector_alloca(self, line: str) -> bool:
        match = _VECTOR_ALLOCA_RE.match(line)
        if match is None:
            return False
        arity_text = match.group("arity").strip()
        vector_size = self._resolve_vector_size(arity_text, match.group("size_arg"))
        wire_ids = tuple(self._allocate_wire_id() for _ in range(vector_size))
        self._vector_aliases[match.group("result")] = wire_ids
        return True

    def _parse_scalar_alloca(self, line: str) -> bool:
        match = _SCALAR_ALLOCA_RE.match(line)
        if match is None:
            return False
        wire_id = self._allocate_wire_id()
        self._ref_aliases[match.group("result")] = wire_id
        return True

    def _parse_extract(self, line: str) -> bool:
        match = _EXTRACT_RE.match(line)
        if match is None:
            return False
        vector_token = match.group("vector")
        if vector_token not in self._vector_aliases:
            raise UnsupportedOperationError(
                f"CUDA-Q adapter could not resolve vector reference {vector_token!r}"
            )
        index = self._resolve_int_token(match.group("index"))
        wire_ids = self._vector_aliases[vector_token]
        if index < 0 or index >= len(wire_ids):
            raise UnsupportedOperationError(
                f"CUDA-Q adapter saw out-of-range vector index {index} for {vector_token!r}"
            )
        self._ref_aliases[match.group("result")] = wire_ids[index]
        return True

    def _parse_unwrap(self, line: str) -> bool:
        match = _UNWRAP_RE.match(line)
        if match is None:
            return False
        self._wire_aliases[match.group("result")] = self._resolve_wire_token(match.group("source"))
        return True

    def _parse_wrap(self, line: str) -> bool:
        return _WRAP_RE.match(line) is not None

    def _parse_operation(self, line: str) -> list[OperationNode]:
        self._reject_control_flow(line)
        assignment_match = _ASSIGNMENT_RE.match(line)
        if assignment_match is None:
            raise UnsupportedOperationError(f"unsupported CUDA-Q Quake statement: {line}")
        result_token = assignment_match.group("result")
        body = assignment_match.group("body").strip()
        if not body.startswith("quake."):
            return []
        body_without_types = body.rsplit(":", 1)[0] if "->" in body else body
        op_name, remainder = self._split_quake_operation(body_without_types)
        controls, remainder = self._parse_controls(remainder)
        parameters, operand_tokens = self._parse_parameters_and_operands(remainder)
        if op_name in {"mz", "mx", "my"}:
            measurements = self._build_measurements(op_name, operand_tokens)
            return list(measurements)
        target_wires = self._resolve_target_wires(operand_tokens)
        operation: OperationIR
        if op_name == "swap":
            if controls:
                raise UnsupportedOperationError(
                    "CUDA-Q swap operations with controls are not supported"
                )
            if len(target_wires) != 2:
                raise UnsupportedOperationError(
                    "CUDA-Q swap operations require exactly two targets"
                )
            operation = OperationIR(
                kind=OperationKind.SWAP,
                name="SWAP",
                target_wires=target_wires,
            )
        elif controls:
            operation = OperationIR(
                kind=OperationKind.CONTROLLED_GATE,
                name=format_gate_name(op_name),
                target_wires=target_wires,
                control_wires=tuple(self._resolve_wire_token(token) for token in controls),
                parameters=parameters,
            )
        else:
            if len(target_wires) != 1:
                raise UnsupportedOperationError(
                    f"CUDA-Q operation '{op_name}' is not supported by the neutral IR"
                )
            operation = OperationIR(
                kind=OperationKind.GATE,
                name=format_gate_name(op_name),
                target_wires=target_wires,
                parameters=parameters,
            )
        if result_token is not None and len(target_wires) == 1:
            self._wire_aliases[result_token] = target_wires[0]
        return [operation]

    def _split_quake_operation(self, body: str) -> tuple[str, str]:
        match = re.match(r"^quake\.(?P<name>\w+)\s*(?P<rest>.*)$", body)
        if match is None:
            raise UnsupportedOperationError(f"unsupported CUDA-Q Quake statement: {body}")
        op_name = match.group("name")
        if op_name in {"reset", "apply", "compute_action", "adjoint"}:
            raise UnsupportedOperationError(
                f"CUDA-Q operation '{op_name}' is outside the supported v0.1 subset"
            )
        return op_name, match.group("rest").strip()

    def _parse_controls(self, remainder: str) -> tuple[tuple[str, ...], str]:
        stripped = remainder.strip()
        if not stripped.startswith("["):
            return (), stripped
        end_index = stripped.find("]")
        if end_index < 0:
            raise UnsupportedOperationError("malformed CUDA-Q controlled operation")
        control_segment = stripped[1:end_index]
        control_tokens = tuple(_SSA_TOKEN_RE.findall(control_segment))
        return control_tokens, stripped[end_index + 1 :].strip()

    def _parse_parameters_and_operands(
        self, remainder: str
    ) -> tuple[tuple[object, ...], tuple[str, ...]]:
        parameters: list[object] = []
        operand_tokens: list[str] = []
        remaining = remainder.strip()
        while remaining.startswith("("):
            group_text, remaining = self._consume_parenthesized_group(remaining)
            group_tokens = _SSA_TOKEN_RE.findall(group_text)
            if not group_tokens:
                parameters.extend(self._extract_numeric_literals(group_text))
                remaining = remaining.strip()
                continue
            if all(self._is_numeric_token(token) for token in group_tokens):
                parameters.extend(self._resolve_numeric_tokens(group_tokens))
            elif all(self._is_operand_token(token) for token in group_tokens):
                operand_tokens.extend(group_tokens)
            else:
                raise UnsupportedOperationError(
                    "CUDA-Q support in v0.1 only supports literal parameters in Quake operations"
                )
            remaining = remaining.strip()
        if remaining:
            operand_tokens.extend(_SSA_TOKEN_RE.findall(remaining))
        return tuple(parameters), tuple(operand_tokens)

    def _build_measurements(
        self, op_name: str, operand_tokens: Sequence[str]
    ) -> tuple[MeasurementIR, ...]:
        if len(operand_tokens) != 1:
            raise UnsupportedOperationError(
                f"CUDA-Q measurement '{op_name}' must reference exactly one wire or register"
            )
        targets = self._resolve_measurement_targets(operand_tokens[0])
        basis = op_name[-1]
        label = op_name.upper()
        measurements: list[MeasurementIR] = []
        for target_wire in targets:
            classical_index = self.measurement_count
            measurements.append(
                MeasurementIR(
                    kind=OperationKind.MEASUREMENT,
                    name=label,
                    label=label,
                    target_wires=(target_wire,),
                    classical_target="c0",
                    metadata={
                        "classical_bit_label": f"c[{classical_index}]",
                        "measurement_basis": basis,
                    },
                )
            )
            self.measurement_count += 1
        return tuple(measurements)

    def _resolve_target_wires(self, operand_tokens: Sequence[str]) -> tuple[str, ...]:
        target_wires = tuple(self._resolve_wire_token(token) for token in operand_tokens)
        if not target_wires:
            raise UnsupportedOperationError("CUDA-Q operation does not reference a drawable target")
        return target_wires

    def _resolve_measurement_targets(self, token: str) -> tuple[str, ...]:
        if token in self._vector_aliases:
            return self._vector_aliases[token]
        return (self._resolve_wire_token(token),)

    def _resolve_wire_token(self, token: str) -> str:
        if token in self._wire_aliases:
            return self._wire_aliases[token]
        if token in self._ref_aliases:
            return self._ref_aliases[token]
        raise UnsupportedOperationError(f"CUDA-Q adapter could not resolve wire token {token!r}")

    def _resolve_vector_size(self, arity_text: str, size_arg: str | None) -> int:
        if arity_text.isdigit():
            return int(arity_text)
        if arity_text != "?":
            raise UnsupportedOperationError(
                f"CUDA-Q vector allocation '{arity_text}' is outside the supported v0.1 subset"
            )
        if size_arg is None:
            raise UnsupportedOperationError(
                "CUDA-Q dynamic qvector sizes are not supported without a literal size"
            )
        return self._resolve_int_token(size_arg)

    def _resolve_int_token(self, token: str) -> int:
        cleaned = token.strip()
        if cleaned.startswith("%"):
            value = self._numeric_aliases.get(cleaned)
            if isinstance(value, (int, float)):
                return int(value)
            raise UnsupportedOperationError(
                f"CUDA-Q adapter could not resolve integer token {cleaned!r}"
            )
        numeric_literal = self._parse_numeric_literal(cleaned)
        if numeric_literal is None:
            raise UnsupportedOperationError(
                f"CUDA-Q adapter could not parse integer token {cleaned!r}"
            )
        return int(numeric_literal)

    def _resolve_numeric_tokens(self, tokens: Sequence[str]) -> tuple[object, ...]:
        values: list[object] = []
        for token in tokens:
            if token.startswith("%"):
                if token not in self._numeric_aliases:
                    raise UnsupportedOperationError(
                        "CUDA-Q support in v0.1 only supports literal parameters in Quake operations"
                    )
                values.append(self._numeric_aliases[token])
                continue
            numeric_literal = self._parse_numeric_literal(token)
            if numeric_literal is None:
                raise UnsupportedOperationError(
                    "CUDA-Q support in v0.1 only supports literal parameters in Quake operations"
                )
            values.append(numeric_literal)
        return tuple(values)

    def _extract_numeric_literals(self, text: str) -> tuple[object, ...]:
        return self._resolve_numeric_tokens(_NUMBER_TOKEN_RE.findall(text))

    def _is_numeric_token(self, token: str) -> bool:
        return token in self._numeric_aliases or self._parse_numeric_literal(token) is not None

    def _is_operand_token(self, token: str) -> bool:
        return (
            token in self._wire_aliases
            or token in self._ref_aliases
            or token in self._vector_aliases
        )

    def _consume_parenthesized_group(self, text: str) -> tuple[str, str]:
        depth = 0
        for index, character in enumerate(text):
            if character == "(":
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    return text[1:index], text[index + 1 :]
        raise UnsupportedOperationError("malformed CUDA-Q operation arguments")

    def _allocate_wire_id(self) -> str:
        wire_id = f"q{self._next_wire_index}"
        self.quantum_wires.append(
            WireIR(
                id=wire_id,
                index=self._next_wire_index,
                kind=WireKind.QUANTUM,
                label=wire_id,
            )
        )
        self._next_wire_index += 1
        return wire_id

    def _parse_numeric_literal(self, token: str) -> int | float | None:
        cleaned = token.strip()
        if cleaned.startswith("dense<") or cleaned in {"true", "false"}:
            return None
        try:
            if any(marker in cleaned for marker in (".", "e", "E")):
                return float(cleaned)
            return int(cleaned)
        except ValueError:
            return None

    def _reject_control_flow(self, line: str) -> None:
        unsupported_prefixes = (
            "cc.if",
            "cc.loop",
            "scf.if",
            "scf.for",
            "cf.cond_br",
        )
        if line.startswith(unsupported_prefixes):
            raise UnsupportedOperationError(
                "CUDA-Q control-flow constructs are outside the supported v0.1 subset"
            )
