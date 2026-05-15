"""Operation-level intermediate representation and canonical gate mapping."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .._compat import StrEnum
from ..typing import Metadata
from .classical_conditions import ClassicalConditionIR


class OperationKind(StrEnum):
    """Operation categories understood by the renderer.

    Values:
        ``GATE`` is a normal gate box, ``CONTROLLED_GATE`` has quantum controls,
        ``SWAP`` draws a swap marker pair, ``BARRIER`` draws a barrier marker, and
        ``MEASUREMENT`` draws a quantum measurement into a classical target.
    """

    GATE = "gate"
    CONTROLLED_GATE = "controlled_gate"
    SWAP = "swap"
    BARRIER = "barrier"
    MEASUREMENT = "measurement"


class CanonicalGateFamily(StrEnum):
    """Framework-independent gate families used for symbols and styling.

    Values:
        The enum includes common single-qubit, controlled, parametric, reset, delay,
        and two-qubit families. ``CUSTOM`` is used when a framework gate name has no
        canonical renderer-specific family.
    """

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


def _canonical_name_token(name: str) -> str:
    """Normalize gate names so aliases map to the same canonical family.

    Framework adapters may emit names with spaces, hyphens, or underscores
    (for example ``"i_swap"``). Rendering should still classify those as
    canonical families so styles and symbols stay consistent.
    """

    return "".join(character for character in name.strip().upper() if character.isalnum())


def _normalize_wire_ids(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


def _normalize_parameters(values: Sequence[object]) -> tuple[object, ...]:
    return tuple(values)


def _normalize_control_values(values: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    return tuple(tuple(int(value) for value in entry) for entry in values)


def _normalize_classical_conditions(
    values: Sequence[ClassicalConditionIR],
) -> tuple[ClassicalConditionIR, ...]:
    return tuple(values)


def _metadata_wire_dependencies(metadata: Metadata) -> tuple[str, ...]:
    value = metadata.get("occupied_wire_dependencies")
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, Sequence):
        return ()
    return tuple(str(wire_id) for wire_id in value if str(wire_id))


def infer_canonical_gate_family(name: str) -> CanonicalGateFamily:
    """Infer a canonical gate family from a display name.

    Args:
        name: Gate name emitted by an adapter or provided by ``CircuitBuilder``.
            Case, spaces, hyphens, and underscores are normalized before matching.

    Returns:
        Matching ``CanonicalGateFamily`` or ``CanonicalGateFamily.CUSTOM`` when no
        known family matches.
    """

    return _CANONICAL_FAMILY_BY_NAME.get(_canonical_name_token(name), CanonicalGateFamily.CUSTOM)


@dataclass(slots=True)
class OperationIR:
    """Framework-neutral description of one drawable operation.

    Attributes:
        kind: ``OperationKind`` describing how the renderer should draw the operation.
        name: Stable operation name. It must not be empty.
        target_wires: Quantum wire ids targeted by the operation. Non-barrier
            operations require at least one target.
        control_wires: Quantum wire ids used as controls.
        control_values: Accepted control values aligned with ``control_wires``. Empty
            means closed controls on ``1``.
        classical_conditions: Classical conditions that gate this operation.
        parameters: Display parameters, such as rotation angles.
        label: Optional visible label. ``None`` defaults to ``name``.
        canonical_family: Optional canonical family. ``CUSTOM`` triggers inference from
            ``name``.
        metadata: Optional adapter metadata used for hover, layout, or provenance.
    """

    kind: OperationKind
    name: str
    target_wires: Sequence[str]
    control_wires: Sequence[str] = field(default_factory=tuple)
    control_values: Sequence[Sequence[int]] = field(default_factory=tuple)
    classical_conditions: Sequence[ClassicalConditionIR] = field(default_factory=tuple)
    parameters: Sequence[object] = field(default_factory=tuple)
    label: str | None = None
    canonical_family: CanonicalGateFamily = CanonicalGateFamily.CUSTOM
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        self.name = normalized_name
        self.target_wires = _normalize_wire_ids(self.target_wires)
        self.control_wires = _normalize_wire_ids(self.control_wires)
        self.control_values = _normalize_control_values(self.control_values)
        self.classical_conditions = _normalize_classical_conditions(self.classical_conditions)
        self.parameters = _normalize_parameters(self.parameters)
        if not normalized_name:
            raise ValueError("operation name cannot be empty")
        if not self.target_wires and self.kind is not OperationKind.BARRIER:
            raise ValueError("operation must reference at least one target wire")
        if self.control_values and len(self.control_values) != len(self.control_wires):
            raise ValueError("control_values must align with control_wires")
        if self.label is None:
            self.label = self.name
        if self.canonical_family is CanonicalGateFamily.CUSTOM:
            self.canonical_family = infer_canonical_gate_family(self.name)

    @property
    def occupied_wire_ids(self) -> tuple[str, ...]:
        """Return every wire id that the operation occupies for layering.

        The returned order is stable and de-duplicated so adapters and layout
        helpers can preserve temporal intent while avoiding slot collisions.
        """

        classical_wire_ids = tuple(
            wire_id for condition in self.classical_conditions for wire_id in condition.wire_ids
        )
        dependency_wire_ids = _metadata_wire_dependencies(self.metadata)
        return tuple(
            dict.fromkeys(
                (*classical_wire_ids, *dependency_wire_ids, *self.control_wires, *self.target_wires)
            )
        )


def resolved_control_values(operation: OperationIR) -> tuple[tuple[int, ...], ...]:
    """Return accepted values for each control wire.

    Args:
        operation: Operation whose quantum controls should be resolved.

    Returns:
        Tuple aligned with ``operation.control_wires``. Missing explicit values default
        to ``(1,)`` for closed controls.
    """

    if operation.control_values:
        return tuple(tuple(entry) for entry in operation.control_values)
    return tuple((1,) for _ in operation.control_wires)


def binary_control_states(operation: OperationIR) -> tuple[int, ...] | None:
    """Return exact binary control states when they can be rendered directly.

    Args:
        operation: Operation whose controls should be inspected.

    Returns:
        Tuple of ``0`` or ``1`` values aligned with ``control_wires``. Returns ``None``
        when any control accepts several values or a non-binary value.
    """

    states: list[int] = []
    for entry in resolved_control_values(operation):
        if len(entry) != 1 or entry[0] not in {0, 1}:
            return None
        states.append(entry[0])
    return tuple(states)
