"""Measurement-specific specialization of the operation IR."""

from __future__ import annotations

from dataclasses import dataclass

from .operations import OperationIR, OperationKind


@dataclass(slots=True)
class MeasurementIR(OperationIR):
    """Framework-neutral measurement operation with a required classical target."""

    classical_target: str | None = None

    def __post_init__(self) -> None:
        OperationIR.__post_init__(self)
        self.kind = OperationKind.MEASUREMENT
        if self.classical_target is None:
            raise ValueError("measurement operations require a classical_target")

    @property
    def occupied_wire_ids(self) -> tuple[str, ...]:
        """Return all occupied wires, including the measurement bit target."""

        base_wires = tuple(
            dict.fromkeys(
                (
                    *self.control_wires,
                    *self.target_wires,
                    *(
                        wire_id
                        for condition in self.classical_conditions
                        for wire_id in condition.wire_ids
                    ),
                )
            )
        )
        classical_target = self.classical_target
        assert classical_target is not None
        return tuple((*base_wires, classical_target))
