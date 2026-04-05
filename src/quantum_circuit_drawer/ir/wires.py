"""Wire-level intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ..typing import Metadata


class WireKind(StrEnum):
    """Supported wire kinds."""

    QUANTUM = "quantum"
    CLASSICAL = "classical"


@dataclass(slots=True)
class WireIR:
    """Neutral wire description."""

    id: str
    index: int
    kind: WireKind
    label: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("wire id cannot be empty")
        if self.label is None:
            self.label = self.id
