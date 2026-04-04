"""Measurement-specific intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass

from .operations import OperationIR, OperationKind


@dataclass(slots=True)
class MeasurementIR(OperationIR):
    """Neutral measurement operation."""

    classical_target: str | None = None

    def __post_init__(self) -> None:
        OperationIR.__post_init__(self)
        self.kind = OperationKind.MEASUREMENT
        if self.classical_target is None:
            raise ValueError("measurement operations require a classical_target")

    @property
    def occupied_wire_ids(self) -> tuple[str, ...]:
        base_wires = tuple(dict.fromkeys((*self.control_wires, *self.target_wires)))
        return tuple((*base_wires, f"classical:{self.classical_target}"))
