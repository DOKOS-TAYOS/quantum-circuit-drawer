"""Shared semantic decompositions for supported canonical two-qubit gates."""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..ir.operations import CanonicalGateFamily, OperationKind
from ..ir.semantic import SemanticOperationIR
from ._helpers import normalized_detail_lines, semantic_provenance

_SUPPORTED_FUNDAMENTAL_DECOMPOSITIONS = frozenset(
    {
        CanonicalGateFamily.RXX,
        CanonicalGateFamily.RYY,
        CanonicalGateFamily.RZZ,
        CanonicalGateFamily.RZX,
    }
)


def expand_fundamental_semantic_gate(
    *,
    framework: str,
    canonical_family: CanonicalGateFamily,
    raw_name: str,
    target_wires: Sequence[str],
    parameters: Sequence[object],
    location: Sequence[int] = (),
) -> tuple[SemanticOperationIR, ...]:
    """Return a shared semantic decomposition for supported canonical families."""

    resolved_wires = tuple(target_wires)
    resolved_parameters = tuple(parameters)
    if canonical_family not in _SUPPORTED_FUNDAMENTAL_DECOMPOSITIONS:
        return ()
    if len(resolved_wires) != 2 or len(resolved_parameters) != 1:
        return ()

    first_wire, second_wire = resolved_wires
    theta = resolved_parameters[0]
    composite_label = str(canonical_family.value)
    base_location = tuple(int(index) for index in location)

    def gate(
        name: str,
        *,
        target_wire: str,
        nested_index: int,
        parameters: Sequence[object] = (),
    ) -> SemanticOperationIR:
        return SemanticOperationIR(
            kind=OperationKind.GATE,
            name=name,
            target_wires=(target_wire,),
            parameters=tuple(parameters),
            hover_details=normalized_detail_lines(f"decomposed from: {composite_label}"),
            provenance=semantic_provenance(
                framework=framework,
                native_name=name,
                native_kind="gate",
                decomposition_origin=raw_name,
                composite_label=composite_label,
                location=(*base_location, nested_index),
            ),
        )

    def controlled_x(
        *,
        control_wire: str,
        target_wire: str,
        nested_index: int,
    ) -> SemanticOperationIR:
        return SemanticOperationIR(
            kind=OperationKind.CONTROLLED_GATE,
            name="X",
            target_wires=(target_wire,),
            control_wires=(control_wire,),
            hover_details=normalized_detail_lines(f"decomposed from: {composite_label}"),
            provenance=semantic_provenance(
                framework=framework,
                native_name="CX",
                native_kind="controlled_gate",
                decomposition_origin=raw_name,
                composite_label=composite_label,
                location=(*base_location, nested_index),
            ),
        )

    if canonical_family is CanonicalGateFamily.RZZ:
        return (
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=0),
            gate("RZ", target_wire=second_wire, nested_index=1, parameters=(theta,)),
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=2),
        )
    if canonical_family is CanonicalGateFamily.RZX:
        return (
            gate("H", target_wire=second_wire, nested_index=0),
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=1),
            gate("RZ", target_wire=second_wire, nested_index=2, parameters=(theta,)),
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=3),
            gate("H", target_wire=second_wire, nested_index=4),
        )
    if canonical_family is CanonicalGateFamily.RXX:
        return (
            gate("H", target_wire=first_wire, nested_index=0),
            gate("H", target_wire=second_wire, nested_index=1),
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=2),
            gate("RZ", target_wire=second_wire, nested_index=3, parameters=(theta,)),
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=4),
            gate("H", target_wire=first_wire, nested_index=5),
            gate("H", target_wire=second_wire, nested_index=6),
        )
    if canonical_family is CanonicalGateFamily.RYY:
        return (
            gate("RX", target_wire=first_wire, nested_index=0, parameters=(math.pi / 2.0,)),
            gate("RX", target_wire=second_wire, nested_index=1, parameters=(math.pi / 2.0,)),
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=2),
            gate("RZ", target_wire=second_wire, nested_index=3, parameters=(theta,)),
            controlled_x(control_wire=first_wire, target_wire=second_wire, nested_index=4),
            gate("RX", target_wire=first_wire, nested_index=5, parameters=(-math.pi / 2.0,)),
            gate("RX", target_wire=second_wire, nested_index=6, parameters=(-math.pi / 2.0,)),
        )
    return ()
