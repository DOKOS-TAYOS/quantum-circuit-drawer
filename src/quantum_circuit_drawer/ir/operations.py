"""Operation-level intermediate representation."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from ..typing import Metadata
from .classical_conditions import ClassicalConditionIR


class OperationKind(StrEnum):
    """Supported operation categories."""

    GATE = "gate"
    CONTROLLED_GATE = "controlled_gate"
    SWAP = "swap"
    BARRIER = "barrier"
    MEASUREMENT = "measurement"


class CanonicalGateFamily(StrEnum):
    """Framework-independent gate families used for canonical rendering."""

    CUSTOM = "custom"
    I = "I"  # noqa: E741
    H = "H"
    X = "X"
    Y = "Y"
    Z = "Z"
    S = "S"
    SDG = "SDG"
    T = "T"
    TDG = "TDG"
    SX = "SX"
    SXDG = "SXDG"
    P = "P"
    RX = "RX"
    RY = "RY"
    RZ = "RZ"
    RXX = "RXX"
    RYY = "RYY"
    RZZ = "RZZ"
    RZX = "RZX"
    U = "U"
    U2 = "U2"
    RESET = "RESET"
    DELAY = "DELAY"
    ECR = "ECR"
    FSIM = "FSIM"
    ISWAP = "ISWAP"


_CANONICAL_FAMILY_BY_NAME: dict[str, CanonicalGateFamily] = {
    "I": CanonicalGateFamily.I,
    "H": CanonicalGateFamily.H,
    "X": CanonicalGateFamily.X,
    "Y": CanonicalGateFamily.Y,
    "Z": CanonicalGateFamily.Z,
    "S": CanonicalGateFamily.S,
    "SDG": CanonicalGateFamily.SDG,
    "T": CanonicalGateFamily.T,
    "TDG": CanonicalGateFamily.TDG,
    "SX": CanonicalGateFamily.SX,
    "SXDG": CanonicalGateFamily.SXDG,
    "P": CanonicalGateFamily.P,
    "RX": CanonicalGateFamily.RX,
    "RY": CanonicalGateFamily.RY,
    "RZ": CanonicalGateFamily.RZ,
    "RXX": CanonicalGateFamily.RXX,
    "RYY": CanonicalGateFamily.RYY,
    "RZZ": CanonicalGateFamily.RZZ,
    "RZX": CanonicalGateFamily.RZX,
    "U": CanonicalGateFamily.U,
    "U2": CanonicalGateFamily.U2,
    "RESET": CanonicalGateFamily.RESET,
    "DELAY": CanonicalGateFamily.DELAY,
    "ECR": CanonicalGateFamily.ECR,
    "FSIM": CanonicalGateFamily.FSIM,
    "ISWAP": CanonicalGateFamily.ISWAP,
}


def _normalize_wire_ids(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


def _normalize_parameters(values: Sequence[object]) -> tuple[object, ...]:
    return tuple(values)


def _normalize_classical_conditions(
    values: Sequence[ClassicalConditionIR],
) -> tuple[ClassicalConditionIR, ...]:
    return tuple(values)


def infer_canonical_gate_family(name: str) -> CanonicalGateFamily:
    """Infer the canonical gate family from a display name."""

    return _CANONICAL_FAMILY_BY_NAME.get(name.strip().upper(), CanonicalGateFamily.CUSTOM)


@dataclass(slots=True)
class OperationIR:
    """Neutral operation description."""

    kind: OperationKind
    name: str
    target_wires: Sequence[str]
    control_wires: Sequence[str] = field(default_factory=tuple)
    classical_conditions: Sequence[ClassicalConditionIR] = field(default_factory=tuple)
    parameters: Sequence[object] = field(default_factory=tuple)
    label: str | None = None
    canonical_family: CanonicalGateFamily = CanonicalGateFamily.CUSTOM
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.target_wires = _normalize_wire_ids(self.target_wires)
        self.control_wires = _normalize_wire_ids(self.control_wires)
        self.classical_conditions = _normalize_classical_conditions(self.classical_conditions)
        self.parameters = _normalize_parameters(self.parameters)
        if not self.name:
            raise ValueError("operation name cannot be empty")
        if not self.target_wires and self.kind is not OperationKind.BARRIER:
            raise ValueError("operation must reference at least one target wire")
        if self.label is None:
            self.label = self.name
        if self.canonical_family is CanonicalGateFamily.CUSTOM:
            self.canonical_family = infer_canonical_gate_family(self.name)

    @property
    def occupied_wire_ids(self) -> tuple[str, ...]:
        classical_wire_ids = tuple(
            wire_id for condition in self.classical_conditions for wire_id in condition.wire_ids
        )
        return tuple(dict.fromkeys((*classical_wire_ids, *self.control_wires, *self.target_wires)))
