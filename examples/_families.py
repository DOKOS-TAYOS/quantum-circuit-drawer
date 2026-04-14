"""Shared circuit families used by the example entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Literal

OperationName = Literal["h", "x", "rx", "ry", "rz", "cx", "cz", "swap"]


@dataclass(frozen=True, slots=True)
class OperationSpec:
    """One framework-agnostic operation for the example builders."""

    name: OperationName
    wires: tuple[int, ...]
    angle: float | None = None


@dataclass(frozen=True, slots=True)
class ColumnSpec:
    """A logical circuit column used by the random demos."""

    operations: tuple[OperationSpec, ...]


@dataclass(frozen=True, slots=True)
class QaoaLayerSpec:
    """Angles for one QAOA layer."""

    gamma: float
    beta: float


def build_random_columns(*, qubits: int, columns: int, seed: int) -> tuple[ColumnSpec, ...]:
    """Build a deterministic random-looking family of circuit columns."""

    if qubits < 1:
        raise ValueError("qubits must be at least 1")
    if columns < 1:
        raise ValueError("columns must be at least 1")

    rng = Random(seed)
    single_qubit_gates: tuple[OperationName, ...] = ("h", "x", "rx", "ry", "rz")
    two_qubit_gates: tuple[OperationName, ...] = ("cx", "cz", "swap")
    built_columns: list[ColumnSpec] = []

    for column_index in range(columns):
        operations: list[OperationSpec] = []
        if column_index % 2 == 0:
            for wire in range(qubits):
                gate_name = single_qubit_gates[
                    (column_index + wire + rng.randrange(len(single_qubit_gates)))
                    % len(single_qubit_gates)
                ]
                angle = None if gate_name in {"h", "x"} else _angle_for(rng, column_index, wire)
                operations.append(OperationSpec(name=gate_name, wires=(wire,), angle=angle))
        else:
            shuffled_wires = list(range(qubits))
            rng.shuffle(shuffled_wires)
            for pair_index in range(0, len(shuffled_wires) - 1, 2):
                left = shuffled_wires[pair_index]
                right = shuffled_wires[pair_index + 1]
                gate_name = two_qubit_gates[
                    (column_index + pair_index + seed) % len(two_qubit_gates)
                ]
                if gate_name != "swap" and (column_index + pair_index + seed) % 2 == 1:
                    left, right = right, left
                operations.append(OperationSpec(name=gate_name, wires=(left, right)))
            if len(shuffled_wires) % 2 == 1:
                leftover_wire = shuffled_wires[-1]
                single_name: OperationName = "rx" if column_index % 4 == 1 else "rz"
                operations.append(
                    OperationSpec(
                        name=single_name,
                        wires=(leftover_wire,),
                        angle=_angle_for(rng, column_index, leftover_wire),
                    )
                )
        built_columns.append(ColumnSpec(operations=tuple(operations)))

    return tuple(built_columns)


def build_cycle_edges(qubits: int) -> tuple[tuple[int, int], ...]:
    """Return the cycle edges used by the QAOA demos."""

    if qubits < 2:
        return ()
    if qubits == 2:
        return ((0, 1),)
    return tuple((wire, (wire + 1) % qubits) for wire in range(qubits))


def build_qaoa_layers(*, layers: int) -> tuple[QaoaLayerSpec, ...]:
    """Return smoothly varying QAOA parameters for the requested depth."""

    if layers < 1:
        raise ValueError("layers must be at least 1")

    built_layers: list[QaoaLayerSpec] = []
    for layer_index in range(layers):
        position = (layer_index + 1) / (layers + 1)
        built_layers.append(
            QaoaLayerSpec(
                gamma=round(0.35 + (0.55 * position), 2),
                beta=round(0.62 - (0.26 * position), 2),
            )
        )
    return tuple(built_layers)


def _angle_for(rng: Random, column_index: int, wire: int) -> float:
    base = 0.18 + (0.07 * ((column_index + wire) % 5))
    return round(base + (0.11 * (wire + 1)) + rng.uniform(0.03, 0.31), 2)
