"""Wire-level intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..typing import Metadata


class WireKind(StrEnum):
    """Kinds of wires that can appear in public IR objects.

    Values:
        ``QUANTUM`` marks wires that carry qubit operations. ``CLASSICAL`` marks wires
        used for measurement results, classical conditions, and classical register
        display.
    """

    QUANTUM = "quantum"
    CLASSICAL = "classical"


def _normalize_wire_kind(value: WireKind | str) -> WireKind:
    try:
        return value if isinstance(value, WireKind) else WireKind(str(value))
    except ValueError as exc:
        choices = ", ".join(kind.value for kind in WireKind)
        raise ValueError(f"wire kind must be one of: {choices}") from exc


@dataclass(slots=True)
class WireIR:
    """Framework-neutral wire description.

    Attributes:
        id: Unique stable wire identifier used by operations and measurements.
        index: Source-order index within its quantum or classical register group.
        kind: ``WireKind.QUANTUM`` or ``WireKind.CLASSICAL``.
        label: Human-facing text drawn next to the wire. ``None`` defaults to ``id``.
        metadata: Optional framework metadata preserved for adapters and extensions.
    """

    id: str
    index: int
    kind: WireKind
    label: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.kind = _normalize_wire_kind(self.kind)
        if not self.id:
            raise ValueError("wire id cannot be empty")
        if self.label is None:
            self.label = self.id
