"""Shared helpers for optional framework adapters."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from types import ModuleType
from typing import TypeVar

from ..ir.classical_conditions import ClassicalConditionIR
from ..ir.measurements import MeasurementIR
from ..ir.operations import CanonicalGateFamily, OperationIR, infer_canonical_gate_family
from ..ir.wires import WireIR, WireKind

OperationNode = OperationIR | MeasurementIR
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class CanonicalGateSpec:
    """Canonical label and family used for cross-framework gate rendering."""

    label: str
    family: CanonicalGateFamily


_ADJOINT_WRAPPER_RE = re.compile(
    r"^(?P<wrapper>adjoint|inverse|dagger)\((?P<inner>[^()]+)\)$",
    flags=re.IGNORECASE,
)

_CANONICAL_LABEL_BY_ALIAS: dict[str, str] = {
    "I": "I",
    "ID": "I",
    "IDENTITY": "I",
    "H": "H",
    "HADAMARD": "H",
    "CH": "H",
    "X": "X",
    "PAULIX": "X",
    "NOT": "X",
    "CX": "X",
    "CNOT": "X",
    "CCX": "X",
    "TOFFOLI": "X",
    "Y": "Y",
    "PAULIY": "Y",
    "CY": "Y",
    "Z": "Z",
    "PAULIZ": "Z",
    "CZ": "Z",
    "S": "S",
    "CS": "S",
    "SDG": "Sdg",
    "CSDG": "Sdg",
    "ADJOINTS": "Sdg",
    "INVERSES": "Sdg",
    "DAGGERS": "Sdg",
    "T": "T",
    "CT": "T",
    "TDG": "Tdg",
    "CTDG": "Tdg",
    "ADJOINTT": "Tdg",
    "INVERSET": "Tdg",
    "DAGGERT": "Tdg",
    "SX": "SX",
    "CSX": "SX",
    "SXDG": "SXdg",
    "ADJOINTSX": "SXdg",
    "INVERSESX": "SXdg",
    "DAGGERSX": "SXdg",
    "P": "P",
    "PHASE": "P",
    "PHASESHIFT": "P",
    "U1": "P",
    "RX": "RX",
    "RXX": "RXX",
    "CRX": "RX",
    "RY": "RY",
    "RYY": "RYY",
    "CRY": "RY",
    "RZ": "RZ",
    "RZZ": "RZZ",
    "ISINGZZ": "RZZ",
    "RZX": "RZX",
    "CRZ": "RZ",
    "U": "U",
    "U3": "U",
    "U2": "U2",
    "RESET": "RESET",
    "RESETCHANNEL": "RESET",
    "DELAY": "DELAY",
    "ECR": "ECR",
    "FSIM": "FSIM",
    "ISWAP": "iSWAP",
}


def load_optional_dependency(module_name: str) -> ModuleType | None:
    """Import an optional dependency and return ``None`` when it is unavailable."""

    try:
        __import__(module_name)
    except ImportError:
        return None

    module = sys.modules.get(module_name)
    if module is None:
        raise ImportError(f"optional dependency {module_name!r} was not loaded")
    return module


def extract_dependency_types(
    module_name: str,
    attribute_paths: Sequence[str],
) -> tuple[type[object], ...]:
    """Return the available runtime types exposed by an optional dependency."""

    module = load_optional_dependency(module_name)
    if module is None:
        return ()

    resolved_types: list[type[object]] = []
    for attribute_path in attribute_paths:
        candidate: object | None = module
        for attribute in attribute_path.split("."):
            candidate = getattr(candidate, attribute, None)
            if candidate is None:
                break
        if isinstance(candidate, type):
            resolved_types.append(candidate)
    return tuple(resolved_types)


def sequential_bit_labels(count: int, *, label: str = "c") -> tuple[str, ...]:
    """Build canonical sequential classical bit labels."""

    return tuple(f"{label}[{index}]" for index in range(count))


def build_classical_register(
    bit_labels: Sequence[str],
    *,
    wire_id: str = "c0",
    wire_index: int = 0,
    label: str = "c",
) -> tuple[list[WireIR], tuple[tuple[str, str], ...]]:
    """Build a single bundled classical register and its bit targets."""

    if not bit_labels:
        return [], ()

    classical_wires = [
        WireIR(
            id=wire_id,
            index=wire_index,
            kind=WireKind.CLASSICAL,
            label=label,
            metadata={"bundle_size": len(bit_labels)},
        )
    ]
    bit_targets = tuple((wire_id, bit_label) for bit_label in bit_labels)
    return classical_wires, bit_targets


def resolve_composite_mode(
    options: Mapping[str, object] | None,
    *,
    default: str = "compact",
) -> str:
    """Return the requested composite-mode override or the default mode."""

    requested_mode = options.get("composite_mode") if options is not None else None
    return str(requested_mode) if requested_mode is not None else default


def append_classical_conditions(
    operation: OperationNode,
    conditions: Sequence[ClassicalConditionIR],
) -> OperationNode:
    """Return a copy of an operation with additional classical conditions."""

    return replace(
        operation,
        classical_conditions=(*operation.classical_conditions, *conditions),
    )


def expand_operation_sequence(
    items: Iterable[_T],
    converter: Callable[[_T], Sequence[OperationNode]],
) -> list[OperationNode]:
    """Expand nested operation sequences while preserving order."""

    expanded: list[OperationNode] = []
    for item in items:
        expanded.extend(converter(item))
    return expanded


def canonical_gate_spec(raw_name: str) -> CanonicalGateSpec:
    """Return the canonical gate label/family for a framework-specific gate name."""

    token = _normalized_gate_token(raw_name)
    label = _CANONICAL_LABEL_BY_ALIAS.get(token)
    if label is not None:
        return CanonicalGateSpec(label=label, family=infer_canonical_gate_family(label))

    compact_label = _compact_custom_gate_label(token or raw_name)
    return CanonicalGateSpec(
        label=compact_label,
        family=infer_canonical_gate_family(compact_label),
    )


def _normalized_gate_token(raw_name: str) -> str:
    normalized_name = raw_name.strip()
    wrapped_match = _ADJOINT_WRAPPER_RE.fullmatch(normalized_name)
    if wrapped_match is not None:
        normalized_name = f"{wrapped_match.group('wrapper')}{wrapped_match.group('inner').strip()}"
    else:
        normalized_name = normalized_name.split("(", 1)[0].strip()

    compact = re.sub(r"[^A-Za-z0-9]+", "", normalized_name)
    compact = re.sub(r"(POWGATE|GATE|POW|OPERATION)$", "", compact, flags=re.IGNORECASE)
    return compact.upper()


def _compact_custom_gate_label(raw_name: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]+", "", raw_name)
    if not compact:
        return "GATE"
    if len(compact) <= 6:
        return compact.upper()
    capitals = "".join(
        character for character in compact if character.isupper() or character.isdigit()
    )
    if 2 <= len(capitals) <= 6:
        return capitals.upper()
    return compact[:6].upper()
