"""Private Quake/MLIR parser used by the CUDA-Q adapter."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from ..exceptions import UnsupportedOperationError
from ..ir.lowering import lower_semantic_operation
from ..ir.operations import OperationKind
from ..ir.semantic import SemanticOperationIR
from ..ir.wires import WireIR, WireKind
from ..utils.formatting import format_gate_name
from ._helpers import canonical_gate_spec, normalized_detail_lines, semantic_provenance
from .base import OperationNode

_ASSIGNMENT_RE = re.compile(r"^(?:(?P<result>%[\w$.]+)\s*=\s*)?(?P<body>.+)$")
_CONSTANT_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*arith\.constant\s+(?P<value>[^:]+)\s*:\s*(?P<type>\S+)$"
)
_CAST_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*arith\.(?:extsi|index_cast|trunci|sitofp|fptosi|extf|truncf)\s+"
    r"(?P<source>%[\w$.]+)\s*:\s*.+$"
)
_LOAD_RE = re.compile(r"^(?P<result>%[\w$.]+)\s*=\s*cc\.load\s+(?P<source>%[\w$.]+)\s*:.*$")
_VECTOR_ALLOCA_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*quake\.alloca"
    r"(?:\((?P<size_arg>[^)]*)\))?"
    r"(?:\s*:\s*|\s+)!"
    r"quake\.(?:veq|qvec)<(?P<arity>[^>]+)>"
    r"(?:\[(?P<bracket_size_arg>[^\]]+)\])?\s*$"
)
_SCALAR_ALLOCA_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*quake\.alloca(?:\([^)]*\))?"
    r"(?:\s*:\s*|\s+)!"
    r"quake\.(?:ref|qref)\s*$"
)
_EXTRACT_RE = re.compile(
    r"^(?P<result>%[\w$.]+)\s*=\s*quake\.(?:extract_ref|qextract)\s+"
    r"(?P<vector>%[\w$.]+)\[(?P<index>[^\]]+)\].*$"
)
_UNWRAP_RE = re.compile(r"^(?P<result>%[\w$.]+)\s*=\s*quake\.unwrap\s+(?P<source>%[\w$.]+).*$")
_WRAP_RE = re.compile(r"^quake\.wrap\s+(?P<wire>%[\w$.]+)\s+to\s+(?P<target>%[\w$.]+).*$")
_SSA_TOKEN_RE = re.compile(r"%[\w$.]+")
_SYMBOL_TOKEN_RE = re.compile(r"@[\w$.]+")
_NUMBER_TOKEN_RE = re.compile(r"[-+]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:e[-+]?\d+)?")
_COMPACT_COMPOSITE_LABELS: dict[str, str] = {
    "apply": "APPLY",
    "adjoint": "ADJOINT",
    "compute_action": "COMPUTE/ACTION",
}
_STRUCTURED_CONTROL_FLOW_PREFIXES = ("cc.if", "cc.loop", "scf.if", "scf.for")
_CC_IF_HEADER_RE = re.compile(r"^cc\.if\s*\((?P<condition>.+)\)\s*\{$")
_SCF_IF_HEADER_RE = re.compile(r"^scf\.if\s+(?P<condition>.+?)(?:\s+->.+)?\s*\{$")
_SCF_FOR_HEADER_RE = re.compile(r"^scf\.for\s+(?P<iteration>.+)\s*\{$")


@dataclass(slots=True)
class CudaqQuakeParser:
    mlir: str
    initial_numeric_aliases: Mapping[str, int | float] = field(default_factory=dict)
    quantum_wires: list[WireIR] = field(default_factory=list)
    measurement_count: int = 0
    _next_wire_index: int = 0
    _vector_aliases: dict[str, tuple[str, ...]] = field(default_factory=dict)
    _ref_aliases: dict[str, str] = field(default_factory=dict)
    _wire_aliases: dict[str, str] = field(default_factory=dict)
    _numeric_aliases: dict[str, int | float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._numeric_aliases.update(self.initial_numeric_aliases)

    def parse(self) -> tuple[list[WireIR], list[OperationNode]]:
        quantum_wires, semantic_operations = self.parse_semantic()
        return quantum_wires, [
            lower_semantic_operation(operation) for operation in semantic_operations
        ]

    def parse_semantic(self) -> tuple[list[WireIR], list[SemanticOperationIR]]:
        operations: list[SemanticOperationIR] = []
        lines = self._normalized_mlir_lines()
        line_index = 0
        while line_index < len(lines):
            line = lines[line_index].strip()
            if not line or line in {"module {", "}", "return"}:
                line_index += 1
                continue
            if line.startswith(("func.func", "cc.scope", "attributes", "module attributes")):
                line_index += 1
                continue
            if line.startswith(_STRUCTURED_CONTROL_FLOW_PREFIXES):
                control_flow_operation, next_index = self._parse_control_flow(
                    lines,
                    start_index=line_index,
                    location=(line_index,),
                )
                operations.append(control_flow_operation)
                line_index = next_index
                continue
            if line in {"{", "}"} or line.endswith("{"):
                self._reject_control_flow(line)
                line_index += 1
                continue
            if self._parse_numeric_alias(line):
                line_index += 1
                continue
            if self._parse_vector_alloca(line):
                line_index += 1
                continue
            if self._parse_scalar_alloca(line):
                line_index += 1
                continue
            if self._parse_extract(line):
                line_index += 1
                continue
            if self._parse_unwrap(line):
                line_index += 1
                continue
            if self._parse_wrap(line):
                line_index += 1
                continue
            operations.extend(self._parse_operation(line, location=(line_index,)))
            line_index += 1
        return self.quantum_wires, operations

    def _normalized_mlir_lines(self) -> list[str]:
        normalized_lines: list[str] = []
        split_headers = {"} else {", "} do {", "} step {"}
        for raw_line in self.mlir.splitlines():
            stripped = raw_line.strip()
            if stripped in split_headers:
                normalized_lines.extend(("}", stripped[1:].strip()))
                continue
            normalized_lines.append(raw_line)
        return normalized_lines

    def _parse_control_flow(
        self,
        lines: Sequence[str],
        *,
        start_index: int,
        location: tuple[int, ...],
    ) -> tuple[SemanticOperationIR, int]:
        header = lines[start_index].strip()
        if header.startswith(("cc.if", "scf.if")):
            return self._parse_if_control_flow(
                lines,
                start_index=start_index,
                location=location,
            )
        if header.startswith("scf.for"):
            return self._parse_for_control_flow(
                lines,
                start_index=start_index,
                location=location,
            )
        if header.startswith("cc.loop"):
            return self._parse_loop_control_flow(
                lines,
                start_index=start_index,
                location=location,
            )
        raise UnsupportedOperationError(f"unsupported CUDA-Q control-flow construct: {header}")

    def _parse_if_control_flow(
        self,
        lines: Sequence[str],
        *,
        start_index: int,
        location: tuple[int, ...],
    ) -> tuple[SemanticOperationIR, int]:
        header = lines[start_index].strip()
        true_region_lines, next_index = self._consume_braced_region(lines, start_index)
        false_region_lines: tuple[str, ...] = ()
        if next_index < len(lines) and lines[next_index].strip().startswith("else"):
            false_region_lines, next_index = self._consume_braced_region(lines, next_index)

        target_wires = self._resolve_control_flow_target_wires(
            (true_region_lines, false_region_lines)
        )
        hover_details = [f"control flow: {header.split()[0]}"]
        condition = self._if_condition_text(header)
        if condition is None:
            hover_details.append(f"header: {self._trim_control_flow_header(header)}")
        else:
            hover_details.append(f"condition: {condition}")
        true_count = self._count_region_operations(true_region_lines)
        if false_region_lines:
            hover_details.append("branches: true, false")
            hover_details.append(
                f"block ops: true={true_count}, false={self._count_region_operations(false_region_lines)}"
            )
        else:
            hover_details.append("branches: true only")
            hover_details.append(f"block ops: true={true_count}")
        hover_details.append(f"wires: {', '.join(target_wires)}")

        has_else_branch = bool(false_region_lines)
        label = "IF/ELSE" if has_else_branch else "IF"
        native_name = "scf.if" if header.startswith("scf.if") else "cc.if"
        return (
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name=label,
                label=label,
                target_wires=target_wires,
                hover_details=normalized_detail_lines(*hover_details),
                provenance=semantic_provenance(
                    framework="cudaq",
                    native_name=native_name,
                    native_kind="control_flow",
                    location=location,
                ),
                metadata={"cudaq_control_flow": native_name},
            ),
            next_index,
        )

    def _parse_for_control_flow(
        self,
        lines: Sequence[str],
        *,
        start_index: int,
        location: tuple[int, ...],
    ) -> tuple[SemanticOperationIR, int]:
        header = lines[start_index].strip()
        body_lines, next_index = self._consume_braced_region(lines, start_index)
        target_wires = self._resolve_control_flow_target_wires((body_lines,))

        iteration = self._for_iteration_text(header)
        hover_details = ["control flow: scf.for"]
        if iteration is None:
            hover_details.append(f"header: {self._trim_control_flow_header(header)}")
        else:
            hover_details.append(f"iteration: {iteration}")
        hover_details.append(f"body ops: {self._count_region_operations(body_lines)}")
        hover_details.append(f"wires: {', '.join(target_wires)}")

        return (
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name="FOR",
                label="FOR",
                target_wires=target_wires,
                hover_details=normalized_detail_lines(*hover_details),
                provenance=semantic_provenance(
                    framework="cudaq",
                    native_name="scf.for",
                    native_kind="control_flow",
                    location=location,
                ),
                metadata={"cudaq_control_flow": "scf.for"},
            ),
            next_index,
        )

    def _parse_loop_control_flow(
        self,
        lines: Sequence[str],
        *,
        start_index: int,
        location: tuple[int, ...],
    ) -> tuple[SemanticOperationIR, int]:
        while_lines, next_index = self._consume_braced_region(lines, start_index)
        region_counts: list[tuple[str, int]] = [
            ("while", self._count_region_operations(while_lines))
        ]
        regions: list[tuple[str, ...]] = [while_lines]

        if next_index < len(lines) and lines[next_index].strip().startswith("do"):
            do_lines, next_index = self._consume_braced_region(lines, next_index)
            regions.append(do_lines)
            region_counts.append(("do", self._count_region_operations(do_lines)))
        if next_index < len(lines) and lines[next_index].strip().startswith("step"):
            step_lines, next_index = self._consume_braced_region(lines, next_index)
            regions.append(step_lines)
            region_counts.append(("step", self._count_region_operations(step_lines)))

        target_wires = self._resolve_control_flow_target_wires(tuple(regions))
        hover_details = [
            "control flow: cc.loop",
            f"region count: {len(region_counts)}",
            "region ops: " + ", ".join(f"{name}={count}" for name, count in region_counts),
            f"wires: {', '.join(target_wires)}",
        ]
        return (
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name="LOOP",
                label="LOOP",
                target_wires=target_wires,
                hover_details=normalized_detail_lines(*hover_details),
                provenance=semantic_provenance(
                    framework="cudaq",
                    native_name="cc.loop",
                    native_kind="control_flow",
                    location=location,
                ),
                metadata={"cudaq_control_flow": "cc.loop"},
            ),
            next_index,
        )

    def _consume_braced_region(
        self,
        lines: Sequence[str],
        start_index: int,
    ) -> tuple[tuple[str, ...], int]:
        header = lines[start_index].strip()
        depth = header.count("{") - header.count("}")
        if depth <= 0:
            raise UnsupportedOperationError(f"malformed CUDA-Q control-flow header: {header}")

        region_lines: list[str] = []
        line_index = start_index + 1
        while line_index < len(lines):
            stripped = lines[line_index].strip()
            if stripped and stripped != "}":
                region_lines.append(stripped)
            depth += stripped.count("{") - stripped.count("}")
            line_index += 1
            if depth == 0:
                return tuple(region_lines), line_index
        raise UnsupportedOperationError(f"unterminated CUDA-Q control-flow region: {header}")

    def _resolve_control_flow_target_wires(
        self,
        region_groups: Sequence[Sequence[str]],
    ) -> tuple[str, ...]:
        resolved_wires: list[str] = []
        for region_lines in region_groups:
            for line in region_lines:
                for token in dict.fromkeys(_SSA_TOKEN_RE.findall(line)):
                    if token in self._vector_aliases:
                        resolved_wires.extend(self._vector_aliases[token])
                    elif token in self._wire_aliases:
                        resolved_wires.append(self._wire_aliases[token])
                    elif token in self._ref_aliases:
                        resolved_wires.append(self._ref_aliases[token])

        deduplicated_wires = tuple(dict.fromkeys(resolved_wires))
        if deduplicated_wires:
            return deduplicated_wires

        allocated_wires = tuple(wire.id for wire in self.quantum_wires)
        if allocated_wires:
            return allocated_wires
        raise UnsupportedOperationError(
            "CUDA-Q control-flow construct does not reference any drawable target"
        )

    def _count_region_operations(self, region_lines: Sequence[str]) -> int:
        return sum(
            1
            for line in region_lines
            if line and line not in {"return", "scf.yield"} and not line.endswith("{")
        )

    def _if_condition_text(self, header: str) -> str | None:
        for pattern in (_CC_IF_HEADER_RE, _SCF_IF_HEADER_RE):
            match = pattern.match(header)
            if match is not None:
                return match.group("condition").strip()
        return None

    def _for_iteration_text(self, header: str) -> str | None:
        match = _SCF_FOR_HEADER_RE.match(header)
        if match is None:
            return None
        return match.group("iteration").strip()

    def _trim_control_flow_header(self, header: str) -> str:
        return header[:-1].strip() if header.endswith("{") else header

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
        load_match = _LOAD_RE.match(line)
        if load_match is not None:
            source = load_match.group("source")
            if source in self._numeric_aliases:
                self._numeric_aliases[load_match.group("result")] = self._numeric_aliases[source]
            return True
        return False

    def _parse_vector_alloca(self, line: str) -> bool:
        match = _VECTOR_ALLOCA_RE.match(line)
        if match is None:
            return False
        arity_text = match.group("arity").strip()
        size_arg = match.group("size_arg") or match.group("bracket_size_arg")
        vector_size = self._resolve_vector_size(arity_text, size_arg)
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

    def _parse_operation(
        self,
        line: str,
        *,
        location: tuple[int, ...],
    ) -> list[SemanticOperationIR]:
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
        if op_name == "null_wire":
            if result_token is None:
                return []
            wire_id = self._allocate_wire_id()
            self._wire_aliases[result_token] = wire_id
            return []
        if op_name in {"discriminate", "dealloc"}:
            return []

        controls, remainder = self._parse_controls(remainder)
        parameters, operand_tokens = self._parse_parameters_and_operands(remainder)
        if op_name in {"mz", "mx", "my"}:
            return list(self._build_measurements(op_name, operand_tokens, location=location))
        if op_name == "reset":
            return self._build_resets(operand_tokens, location=location)
        if op_name in _COMPACT_COMPOSITE_LABELS:
            return [
                self._build_compact_callable_operation(
                    op_name,
                    controls=controls,
                    operand_tokens=operand_tokens,
                    raw_remainder=remainder,
                    location=location,
                )
            ]

        target_wires = self._resolve_operand_wires(operand_tokens)
        if op_name == "swap":
            if len(target_wires) != 2:
                raise UnsupportedOperationError(
                    "CUDA-Q swap operations require exactly two targets"
                )
            if controls:
                control_wires = tuple(self._resolve_wire_token(token) for token in controls)
                return [
                    SemanticOperationIR(
                        kind=OperationKind.CONTROLLED_GATE,
                        name="SWAP",
                        label="SWAP",
                        target_wires=target_wires,
                        control_wires=control_wires,
                        hover_details=normalized_detail_lines(
                            "quake: swap",
                            f"controls: {', '.join(control_wires)}",
                            f"targets: {', '.join(target_wires)}",
                        ),
                        provenance=semantic_provenance(
                            framework="cudaq",
                            native_name="swap",
                            native_kind="controlled_swap",
                            location=location,
                        ),
                    )
                ]
            return [
                SemanticOperationIR(
                    kind=OperationKind.SWAP,
                    name="SWAP",
                    target_wires=target_wires,
                    hover_details=normalized_detail_lines("quake: swap"),
                    provenance=semantic_provenance(
                        framework="cudaq",
                        native_name="swap",
                        native_kind="swap",
                        location=location,
                    ),
                )
            ]

        native_label = format_gate_name(op_name)
        canonical_gate = canonical_gate_spec(native_label)
        if controls:
            operation = SemanticOperationIR(
                kind=OperationKind.CONTROLLED_GATE,
                name=canonical_gate.label,
                canonical_family=canonical_gate.family,
                target_wires=target_wires,
                control_wires=tuple(self._resolve_wire_token(token) for token in controls),
                parameters=parameters,
                hover_details=normalized_detail_lines(f"quake: {op_name}"),
                provenance=semantic_provenance(
                    framework="cudaq",
                    native_name=op_name,
                    native_kind="controlled_gate",
                    location=location,
                ),
            )
            if result_token is not None and len(target_wires) == 1:
                self._wire_aliases[result_token] = target_wires[0]
            return [operation]

        if len(target_wires) != 1:
            raise UnsupportedOperationError(
                f"CUDA-Q operation '{op_name}' is not supported by the neutral IR"
            )
        operation = SemanticOperationIR(
            kind=OperationKind.GATE,
            name=canonical_gate.label,
            canonical_family=canonical_gate.family,
            target_wires=target_wires,
            parameters=parameters,
            hover_details=normalized_detail_lines(f"quake: {op_name}"),
            provenance=semantic_provenance(
                framework="cudaq",
                native_name=op_name,
                native_kind="gate",
                location=location,
            ),
        )
        if result_token is not None:
            self._wire_aliases[result_token] = target_wires[0]
        return [operation]

    def _split_quake_operation(self, body: str) -> tuple[str, str]:
        match = re.match(r"^quake\.(?P<name>\w+)\s*(?P<rest>.*)$", body)
        if match is None:
            raise UnsupportedOperationError(f"unsupported CUDA-Q Quake statement: {body}")
        return match.group("name"), match.group("rest").strip()

    def _build_compact_callable_operation(
        self,
        op_name: str,
        *,
        controls: Sequence[str],
        operand_tokens: Sequence[str],
        raw_remainder: str,
        location: tuple[int, ...],
    ) -> SemanticOperationIR:
        target_wires = self._resolve_operand_wires((*controls, *operand_tokens))
        callable_symbols = tuple(dict.fromkeys(_SYMBOL_TOKEN_RE.findall(raw_remainder)))
        hover_details: list[str] = [f"quake: {op_name}"]
        if callable_symbols:
            if len(callable_symbols) == 1:
                hover_details.append(f"callable: {callable_symbols[0]}")
            else:
                hover_details.append(f"callables: {', '.join(callable_symbols)}")
        else:
            hover_details.append(f"raw: {raw_remainder.strip()}")
        hover_details.append(f"wires: {', '.join(target_wires)}")
        return SemanticOperationIR(
            kind=OperationKind.GATE,
            name=_COMPACT_COMPOSITE_LABELS[op_name],
            label=_COMPACT_COMPOSITE_LABELS[op_name],
            target_wires=target_wires,
            hover_details=normalized_detail_lines(*hover_details),
            provenance=semantic_provenance(
                framework="cudaq",
                native_name=op_name,
                native_kind="composite",
                location=location,
            ),
        )

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
        self,
        remainder: str,
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
        self,
        op_name: str,
        operand_tokens: Sequence[str],
        *,
        location: tuple[int, ...],
    ) -> tuple[SemanticOperationIR, ...]:
        if len(operand_tokens) != 1:
            raise UnsupportedOperationError(
                f"CUDA-Q measurement '{op_name}' must reference exactly one wire or register"
            )
        targets = self._resolve_measurement_targets(operand_tokens[0])
        basis = op_name[-1]
        label = op_name.upper()
        measurements: list[SemanticOperationIR] = []
        for measurement_index, target_wire in enumerate(targets):
            classical_index = self.measurement_count
            measurements.append(
                SemanticOperationIR(
                    kind=OperationKind.MEASUREMENT,
                    name=label,
                    label=label,
                    target_wires=(target_wire,),
                    classical_target="c0",
                    hover_details=normalized_detail_lines(f"quake: {op_name}"),
                    provenance=semantic_provenance(
                        framework="cudaq",
                        native_name=op_name,
                        native_kind="measurement",
                        location=(*location, measurement_index),
                    ),
                    metadata={
                        "classical_bit_label": f"c[{classical_index}]",
                        "measurement_basis": basis,
                    },
                )
            )
            self.measurement_count += 1
        return tuple(measurements)

    def _build_resets(
        self,
        operand_tokens: Sequence[str],
        *,
        location: tuple[int, ...],
    ) -> list[SemanticOperationIR]:
        target_wires = self._resolve_operand_wires(operand_tokens)
        if not target_wires:
            raise UnsupportedOperationError("CUDA-Q reset operation requires at least one target")
        return [
            SemanticOperationIR(
                kind=OperationKind.GATE,
                name="RESET",
                target_wires=(target_wire,),
                hover_details=normalized_detail_lines("quake: reset"),
                provenance=semantic_provenance(
                    framework="cudaq",
                    native_name="reset",
                    native_kind="reset",
                    location=(*location, reset_index),
                ),
            )
            for reset_index, target_wire in enumerate(target_wires)
        ]

    def _resolve_operand_wires(self, operand_tokens: Sequence[str]) -> tuple[str, ...]:
        resolved: list[str] = []
        for token in operand_tokens:
            if token in self._vector_aliases:
                resolved.extend(self._vector_aliases[token])
                continue
            resolved.append(self._resolve_wire_token(token))
        target_wires = tuple(resolved)
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
        try:
            return self._resolve_int_token(size_arg)
        except UnsupportedOperationError as exc:
            raise UnsupportedOperationError(
                "CUDA-Q dynamic qvector sizes are not supported without a literal size"
            ) from exc

    def _resolve_int_token(self, token: str) -> int:
        cleaned = token.strip()
        if ":" in cleaned:
            cleaned = cleaned.split(":", 1)[0].strip()
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
        unsupported_prefixes = ("cf.cond_br",)
        if line.startswith(unsupported_prefixes):
            raise UnsupportedOperationError(
                "CUDA-Q control-flow constructs are outside the supported v0.1 subset"
            )
