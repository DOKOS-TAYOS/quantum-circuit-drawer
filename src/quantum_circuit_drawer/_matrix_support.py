"""Helpers for resolving compact operation matrices used by hover rendering."""

from __future__ import annotations

import cmath
from collections.abc import Sequence

import numpy as np

from .ir.operations import CanonicalGateFamily, OperationIR, OperationKind


def square_matrix(matrix: object) -> np.ndarray | None:
    """Return a complex square matrix when the input can be represented as one."""

    try:
        matrix_value = np.asarray(matrix, dtype=np.complex128)
    except (TypeError, ValueError):
        return None
    if matrix_value.ndim != 2 or matrix_value.shape[0] != matrix_value.shape[1]:
        return None
    return matrix_value


def matrix_qubit_count(matrix: np.ndarray) -> int | None:
    """Return the number of qubits represented by a square unitary matrix."""

    dimension = int(matrix.shape[0])
    if dimension <= 0 or dimension & (dimension - 1):
        return None
    return int(np.log2(dimension))


def resolved_operation_matrix(operation: OperationIR) -> np.ndarray | None:
    """Return the best available matrix for an operation."""

    return _resolved_operation_matrix_and_dimension(operation)[0]


def operation_matrix_dimension(operation: OperationIR) -> int | None:
    """Return the matrix dimension for an operation when it is well-defined."""

    return _resolved_operation_matrix_and_dimension(operation)[1]


def _resolved_operation_matrix_and_dimension(
    operation: OperationIR,
) -> tuple[np.ndarray | None, int | None]:
    """Return the best available matrix together with its resolved dimension."""

    resolved_matrix = _resolved_operation_matrix(operation)
    if resolved_matrix is not None:
        return resolved_matrix, int(resolved_matrix.shape[0])

    if operation.kind not in {
        OperationKind.GATE,
        OperationKind.CONTROLLED_GATE,
        OperationKind.SWAP,
    }:
        return None, None

    qubit_count = len(dict.fromkeys((*operation.control_wires, *operation.target_wires)))
    if qubit_count <= 0:
        return None, None
    return None, 1 << qubit_count


def _resolved_operation_matrix(operation: OperationIR) -> np.ndarray | None:
    explicit_matrix = square_matrix(operation.metadata.get("matrix"))
    if explicit_matrix is not None:
        return explicit_matrix
    return inferred_operation_matrix(operation)


def inferred_operation_matrix(operation: OperationIR) -> np.ndarray | None:
    """Return a canonical fallback matrix when the operation is unambiguous."""

    if operation.kind is OperationKind.SWAP:
        return _swap_matrix()
    if operation.kind is OperationKind.CONTROLLED_GATE:
        return _controlled_operation_matrix(operation)
    if operation.kind is not OperationKind.GATE:
        return None

    qubit_count = len(operation.target_wires)
    if qubit_count == 1:
        return _single_qubit_gate_matrix(operation.canonical_family, operation.parameters)
    if qubit_count == 2:
        return _two_qubit_gate_matrix(operation.canonical_family, operation.parameters)
    return None


def _controlled_operation_matrix(operation: OperationIR) -> np.ndarray | None:
    if len(operation.control_wires) != 1 or len(operation.target_wires) != 1:
        return None

    target_matrix = _single_qubit_gate_matrix(operation.canonical_family, operation.parameters)
    if target_matrix is None:
        return None

    matrix = np.eye(4, dtype=np.complex128)
    matrix[2:, 2:] = target_matrix
    return matrix


def _single_qubit_gate_matrix(
    family: CanonicalGateFamily,
    parameters: Sequence[object],
) -> np.ndarray | None:
    if family is CanonicalGateFamily.I:
        return np.array(((1.0, 0.0), (0.0, 1.0)), dtype=np.complex128)
    if family is CanonicalGateFamily.H:
        return np.array(((1.0, 1.0), (1.0, -1.0)), dtype=np.complex128) / np.sqrt(2.0)
    if family is CanonicalGateFamily.X:
        return np.array(((0.0, 1.0), (1.0, 0.0)), dtype=np.complex128)
    if family is CanonicalGateFamily.Y:
        return np.array(((0.0, -1j), (1j, 0.0)), dtype=np.complex128)
    if family is CanonicalGateFamily.Z:
        return np.array(((1.0, 0.0), (0.0, -1.0)), dtype=np.complex128)
    if family is CanonicalGateFamily.S:
        return np.array(((1.0, 0.0), (0.0, 1j)), dtype=np.complex128)
    if family is CanonicalGateFamily.SDG:
        return np.array(((1.0, 0.0), (0.0, -1j)), dtype=np.complex128)
    if family is CanonicalGateFamily.T:
        return np.array(((1.0, 0.0), (0.0, cmath.exp(1j * np.pi / 4.0))), dtype=np.complex128)
    if family is CanonicalGateFamily.TDG:
        return np.array(((1.0, 0.0), (0.0, cmath.exp(-1j * np.pi / 4.0))), dtype=np.complex128)
    if family is CanonicalGateFamily.SX:
        return np.array(
            (
                ((1.0 + 1j) / 2.0, (1.0 - 1j) / 2.0),
                ((1.0 - 1j) / 2.0, (1.0 + 1j) / 2.0),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.SXDG:
        sx_matrix = _single_qubit_gate_matrix(CanonicalGateFamily.SX, ())
        assert sx_matrix is not None
        return np.conjugate(sx_matrix).T
    if family is CanonicalGateFamily.P:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        return np.array(((1.0, 0.0), (0.0, cmath.exp(1j * theta))), dtype=np.complex128)
    if family is CanonicalGateFamily.RX:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        cosine = cmath.cos(theta / 2.0)
        sine = cmath.sin(theta / 2.0)
        return np.array(((cosine, -1j * sine), (-1j * sine, cosine)), dtype=np.complex128)
    if family is CanonicalGateFamily.RY:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        cosine = cmath.cos(theta / 2.0)
        sine = cmath.sin(theta / 2.0)
        return np.array(((cosine, -sine), (sine, cosine)), dtype=np.complex128)
    if family is CanonicalGateFamily.RZ:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        return np.array(
            (
                (cmath.exp(-1j * theta / 2.0), 0.0),
                (0.0, cmath.exp(1j * theta / 2.0)),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.U:
        theta, phi, lam = _coerce_real_parameters(parameters, 3)
        if theta is None or phi is None or lam is None:
            return None
        cosine = cmath.cos(theta / 2.0)
        sine = cmath.sin(theta / 2.0)
        return np.array(
            (
                (cosine, -cmath.exp(1j * lam) * sine),
                (cmath.exp(1j * phi) * sine, cmath.exp(1j * (phi + lam)) * cosine),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.U2:
        phi, lam = _coerce_real_parameters(parameters, 2)
        if phi is None or lam is None:
            return None
        return _single_qubit_gate_matrix(CanonicalGateFamily.U, (np.pi / 2.0, phi, lam))
    return None


def _two_qubit_gate_matrix(
    family: CanonicalGateFamily,
    parameters: Sequence[object],
) -> np.ndarray | None:
    if family is CanonicalGateFamily.RXX:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        cosine = cmath.cos(theta / 2.0)
        sine = cmath.sin(theta / 2.0)
        return np.array(
            (
                (cosine, 0.0, 0.0, -1j * sine),
                (0.0, cosine, -1j * sine, 0.0),
                (0.0, -1j * sine, cosine, 0.0),
                (-1j * sine, 0.0, 0.0, cosine),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.RYY:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        cosine = cmath.cos(theta / 2.0)
        sine = cmath.sin(theta / 2.0)
        return np.array(
            (
                (cosine, 0.0, 0.0, 1j * sine),
                (0.0, cosine, -1j * sine, 0.0),
                (0.0, -1j * sine, cosine, 0.0),
                (1j * sine, 0.0, 0.0, cosine),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.RZZ:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        leading = cmath.exp(-1j * theta / 2.0)
        inner = cmath.exp(1j * theta / 2.0)
        return np.array(
            (
                (leading, 0.0, 0.0, 0.0),
                (0.0, inner, 0.0, 0.0),
                (0.0, 0.0, inner, 0.0),
                (0.0, 0.0, 0.0, leading),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.RZX:
        theta = _coerce_real_parameter(parameters)
        if theta is None:
            return None
        cosine = cmath.cos(theta / 2.0)
        sine = cmath.sin(theta / 2.0)
        return np.array(
            (
                (cosine, 0.0, -1j * sine, 0.0),
                (0.0, cosine, 0.0, 1j * sine),
                (-1j * sine, 0.0, cosine, 0.0),
                (0.0, 1j * sine, 0.0, cosine),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.ECR:
        return np.array(
            (
                (0.0, 1.0, 0.0, 1j),
                (1.0, 0.0, -1j, 0.0),
                (0.0, 1j, 0.0, 1.0),
                (-1j, 0.0, 1.0, 0.0),
            ),
            dtype=np.complex128,
        ) / np.sqrt(2.0)
    if family is CanonicalGateFamily.FSIM:
        theta, phi = _coerce_real_parameters(parameters, 2)
        if theta is None or phi is None:
            return None
        cosine = cmath.cos(theta)
        sine = cmath.sin(theta)
        return np.array(
            (
                (1.0, 0.0, 0.0, 0.0),
                (0.0, cosine, -1j * sine, 0.0),
                (0.0, -1j * sine, cosine, 0.0),
                (0.0, 0.0, 0.0, cmath.exp(-1j * phi)),
            ),
            dtype=np.complex128,
        )
    if family is CanonicalGateFamily.ISWAP:
        return np.array(
            (
                (1.0, 0.0, 0.0, 0.0),
                (0.0, 0.0, 1j, 0.0),
                (0.0, 1j, 0.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            ),
            dtype=np.complex128,
        )
    return None


def _swap_matrix() -> np.ndarray:
    return np.array(
        (
            (1.0, 0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
            (0.0, 0.0, 0.0, 1.0),
        ),
        dtype=np.complex128,
    )


def _coerce_real_scalar_parameter(parameter: object) -> float | None:
    try:
        numeric = np.asarray(parameter, dtype=np.complex128)
    except (TypeError, ValueError):
        return None
    if numeric.ndim != 0:
        return None

    scalar = complex(numeric.item())
    if abs(scalar.imag) > 1e-12:
        return None
    return float(scalar.real)


def _coerce_real_parameter(parameters: Sequence[object]) -> float | None:
    if len(parameters) != 1:
        return None
    return _coerce_real_scalar_parameter(parameters[0])


def _coerce_real_parameters(
    parameters: Sequence[object],
    expected_count: int,
) -> tuple[float | None, ...]:
    if len(parameters) != expected_count:
        return tuple(None for _ in range(expected_count))

    values: list[float] = []
    for parameter in parameters:
        resolved = _coerce_real_scalar_parameter(parameter)
        if resolved is None:
            return tuple(None for _ in range(expected_count))
        values.append(resolved)
    return tuple(values)
