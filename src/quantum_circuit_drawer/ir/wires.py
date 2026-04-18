"""Wire-level intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field

from .._compat import StrEnum
from ..typing import Metadata


class WireKind(StrEnum):
    """Supported wire kinds."""

    QUANTUM = "quantum"
    CLASSICAL = "classical"


@dataclass(slots=True)
class WireIR:
    """Framework-neutral wire description.

    ``index`` preserves source ordering, while ``label`` stores the human-facing
    text drawn next to the wire. When omitted, the label defaults to ``id``.
    """

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
