"""Shared helpers for optional framework adapters."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
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
    "CSIGN": "Z",
    "S": "S",
    "CS": "S",
    "SDG": "Sdg",
    "DS": "Sdg",
    "CSDG": "Sdg",
    "ADJOINTS": "Sdg",
    "INVERSES": "Sdg",
    "DAGGERS": "Sdg",
    "T": "T",
    "CT": "T",
    "TDG": "Tdg",
    "DT": "Tdg",
    "CTDG": "Tdg",
    "ADJOINTT": "Tdg",
    "INVERSET": "Tdg",
    "DAGGERT": "Tdg",
    "SX": "SX",
    "CSX": "SX",
    "SXDG": "SXdg",
    "DSX": "SXdg",
    "ADJOINTSX": "SXdg",
    "INVERSESX": "SXdg",
    "DAGGERSX": "SXdg",
    "P": "P",
    "PH": "P",
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

_MATRIX_UNAVAILABLE_ERROR_NAMES = frozenset(
    {
        "CircuitError",
        "MatrixUndefinedError",
        "QiskitError",
        "TransformError",
    }
)


def load_optional_dependency(module_name: str) -> ModuleType | None:
    """Import an optional dependency and return ``None`` when it is unavailable."""

    try:
        __import__(module_name)
    except ModuleNotFoundError as exc:
        if _matches_missing_module(exc, module_name):
            return None
        raise

    module = sys.modules.get(module_name)
    if module is None:
        raise ImportError(f"optional dependency {module_name!r} was not loaded")
    return module


def extract_dependency_types(
    module_name: str,
    attribute_paths: Sequence[str],
) -> tuple[type[object], ...]:
    """Return the available runtime types exposed by an optional dependency."""

    normalized_paths = tuple(attribute_paths)
    return _extract_dependency_types_cached(
        module_name,
        normalized_paths,
        _dependency_resolution_state(module_name, normalized_paths),
    )


@lru_cache(maxsize=128)
def _extract_dependency_types_cached(
    module_name: str,
    attribute_paths: tuple[str, ...],
    resolution_state: tuple[object, ...],
) -> tuple[type[object], ...]:
    """Cached implementation for resolving dependency runtime types."""

    del resolution_state
    module = load_optional_dependency(module_name)
    if module is None:
        return ()

    resolved_types: list[type[object]] = []
    for attribute_path in attribute_paths:
        candidate = _resolve_dependency_candidate(module_name, module, attribute_path)
        if isinstance(candidate, type):
            resolved_types.append(candidate)
    return tuple(resolved_types)


def _dependency_resolution_state(
    module_name: str,
    attribute_paths: tuple[str, ...],
) -> tuple[object, ...]:
    """Return the import state that determines optional type resolution."""

    state: list[object] = [_cache_state_value(__import__)]
    top_level_module = sys.modules.get(module_name)
    state.extend((module_name, _cache_state_value(top_level_module)))
    for attribute_path in attribute_paths:
        state.extend(_attribute_path_resolution_state(module_name, attribute_path))
    return tuple(state)


def _attribute_path_resolution_state(
    module_name: str,
    attribute_path: str,
) -> tuple[object, ...]:
    """Return the current module/attribute chain state for one dependency path."""

    state: list[object] = []
    candidate: object | None = sys.modules.get(module_name)
    current_module_name = module_name
    path_parts = attribute_path.split(".")
    last_index = len(path_parts) - 1

    for index, attribute in enumerate(path_parts):
        next_candidate = getattr(candidate, attribute, None)
        state.extend(
            (
                current_module_name,
                attribute,
                _cache_state_value(next_candidate),
            )
        )
        if next_candidate is not None:
            candidate = next_candidate
            if isinstance(candidate, ModuleType):
                current_module_name = candidate.__name__
                state.extend(
                    (
                        current_module_name,
                        _cache_state_value(candidate),
                    )
                )
            continue
        if index == last_index or not isinstance(candidate, ModuleType):
            candidate = None
            continue

        qualified_name = f"{current_module_name}.{attribute}"
        imported_submodule = sys.modules.get(qualified_name)
        state.extend(
            (
                qualified_name,
                _cache_state_value(imported_submodule),
            )
        )
        candidate = imported_submodule
        current_module_name = qualified_name
    return tuple(state)


def _cache_state_value(value: object | None) -> object | None:
    """Return a hashable cache token component for one resolution value."""

    if value is None:
        return None
    try:
        hash(value)
    except TypeError:
        return ("id", type(value), id(value))
    return value


def _resolve_dependency_candidate(
    module_name: str,
    module: ModuleType,
    attribute_path: str,
) -> object | None:
    candidate: object = module
    current_module_name = module_name
    path_parts = attribute_path.split(".")
    last_index = len(path_parts) - 1

    for index, attribute in enumerate(path_parts):
        next_candidate = getattr(candidate, attribute, None)
        if next_candidate is not None:
            candidate = next_candidate
            if isinstance(candidate, ModuleType):
                current_module_name = candidate.__name__
            continue
        if index == last_index or not isinstance(candidate, ModuleType):
            return None

        imported_submodule = _load_optional_submodule(current_module_name, attribute)
        if imported_submodule is None:
            return None
        candidate = imported_submodule
        current_module_name = imported_submodule.__name__
    return candidate


def _load_optional_submodule(
    parent_module_name: str,
    submodule_name: str,
) -> ModuleType | None:
    qualified_name = f"{parent_module_name}.{submodule_name}"
    try:
        __import__(qualified_name)
    except ModuleNotFoundError as exc:
        if _matches_missing_module(exc, qualified_name):
            return None
        raise

    module = sys.modules.get(qualified_name)
    if module is None:
        raise ImportError(f"optional dependency submodule {qualified_name!r} was not loaded")
    return module


def _matches_missing_module(exc: ModuleNotFoundError, module_name: str) -> bool:
    missing_name = getattr(exc, "name", None)
    if missing_name == module_name:
        return True
    return bool(exc.args) and exc.args[0] == module_name


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


def resolve_explicit_matrices(
    options: Mapping[str, object] | None,
    *,
    default: bool = True,
) -> bool:
    """Return whether adapters should request exact framework matrices."""

    requested_value = options.get("explicit_matrices") if options is not None else None
    if requested_value is None:
        return default
    if isinstance(requested_value, bool):
        return requested_value
    return bool(requested_value)


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


def is_expected_matrix_unavailable_error(exc: Exception) -> bool:
    """Return whether a matrix-extraction error means "metadata unavailable"."""

    if isinstance(exc, (AttributeError, NotImplementedError, TypeError, ValueError)):
        return True
    return type(exc).__name__ in _MATRIX_UNAVAILABLE_ERROR_NAMES


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
