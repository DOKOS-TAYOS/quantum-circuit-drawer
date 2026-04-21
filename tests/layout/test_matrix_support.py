from __future__ import annotations

import numpy as np

from quantum_circuit_drawer.ir.operations import OperationIR, OperationKind
from quantum_circuit_drawer.utils.matrix_support import _resolved_operation_matrix_and_dimension


def test_resolved_operation_matrix_and_dimension_prefers_explicit_matrix() -> None:
    explicit_matrix = np.array(((0.0, 1.0), (1.0, 0.0)), dtype=np.complex128)
    operation = OperationIR(
        kind=OperationKind.GATE,
        name="custom_gate",
        target_wires=("q0",),
        metadata={"matrix": explicit_matrix},
    )

    resolved_matrix, matrix_dimension = _resolved_operation_matrix_and_dimension(operation)

    assert matrix_dimension == 2
    assert resolved_matrix is not None
    np.testing.assert_array_equal(resolved_matrix, explicit_matrix)


def test_resolved_operation_matrix_and_dimension_infers_controlled_gate_matrix() -> None:
    operation = OperationIR(
        kind=OperationKind.CONTROLLED_GATE,
        name="X",
        target_wires=("q1",),
        control_wires=("q0",),
    )

    resolved_matrix, matrix_dimension = _resolved_operation_matrix_and_dimension(operation)

    expected_matrix = np.array(
        (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
            (0.0, 0.0, 1.0, 0.0),
        ),
        dtype=np.complex128,
    )

    assert matrix_dimension == 4
    assert resolved_matrix is not None
    np.testing.assert_allclose(resolved_matrix, expected_matrix)


def test_resolved_operation_matrix_and_dimension_infers_open_controlled_gate_matrix() -> None:
    operation = OperationIR(
        kind=OperationKind.CONTROLLED_GATE,
        name="X",
        target_wires=("q1",),
        control_wires=("q0",),
        control_values=((0,),),
    )

    resolved_matrix, matrix_dimension = _resolved_operation_matrix_and_dimension(operation)

    expected_matrix = np.array(
        (
            (0.0, 1.0, 0.0, 0.0),
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=np.complex128,
    )

    assert matrix_dimension == 4
    assert resolved_matrix is not None
    np.testing.assert_allclose(resolved_matrix, expected_matrix)
