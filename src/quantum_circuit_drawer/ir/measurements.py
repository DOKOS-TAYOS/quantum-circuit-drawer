"""Measurement-specific specialization of the operation IR."""

from __future__ import annotations

from dataclasses import dataclass

from .operations import OperationIR, OperationKind, _metadata_wire_dependencies


@dataclass(slots=True)
class MeasurementIR(OperationIR):
    """Measurement operation with a required classical target.

    Attributes:
        classical_target: Classical wire id that receives the measurement result. It is
            required and is included in ``occupied_wire_ids`` so layout can draw the
            quantum-to-classical connection.
    """

    classical_target: str | None = None

    def __post_init__(self) -> None:
        OperationIR.__post_init__(self)
        self.kind = OperationKind.MEASUREMENT
        if not self.target_wires:
            raise ValueError("measurement operation must reference at least one target wire")
        if self.classical_target is None:
            raise ValueError("measurement operations require a classical_target")
        self.classical_target = str(self.classical_target)
        if not self.classical_target:
            raise ValueError("measurement classical_target cannot be empty")

    @property
    def occupied_wire_ids(self) -> tuple[str, ...]:
        """Return all occupied wires, including the measurement bit target."""

        classical_wire_ids = tuple(
            wire_id for condition in self.classical_conditions for wire_id in condition.wire_ids
        )
        dependency_wire_ids = _metadata_wire_dependencies(self.metadata)
        base_wires = tuple(
            dict.fromkeys(
                (*classical_wire_ids, *dependency_wire_ids, *self.control_wires, *self.target_wires)
            )
        )
        classical_target = self.classical_target
        assert classical_target is not None
        return tuple(dict.fromkeys((*base_wires, classical_target)))
