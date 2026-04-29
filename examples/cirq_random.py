"""Configurable random-looking Cirq example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
from random import Random

from cirq.circuits import Circuit, Moment
from cirq.devices import LineQubit
from cirq.ops import CNOT, CZ, SWAP, H, X, measure, rx, ry, rz
from cirq.ops.raw_types import Operation

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402

DEFAULT_FIGSIZE: tuple[float, float] = (10.1, 5.5)


def build_circuit(*, qubit_count: int, column_count: int, seed: int) -> Circuit:
    """Build a deterministic random-looking Cirq circuit."""

    qubits = LineQubit.range(qubit_count)
    moments: list[Moment] = []
    rng = Random(seed)
    single_qubit_gates = ("h", "x", "rx", "ry", "rz")
    two_qubit_gates = ("cx", "cz", "swap")

    for column_index in range(column_count):
        operations: list[Operation] = []
        if column_index % 2 == 0:
            for wire in range(qubit_count):
                gate_name = single_qubit_gates[
                    (column_index + wire + rng.randrange(len(single_qubit_gates)))
                    % len(single_qubit_gates)
                ]
                operations.append(
                    _single_qubit_operation(
                        qubits[wire],
                        gate_name=gate_name,
                        angle=_angle_for(rng, column_index, wire),
                    )
                )
        else:
            shuffled_wires = list(range(qubit_count))
            rng.shuffle(shuffled_wires)
            for pair_index in range(0, len(shuffled_wires) - 1, 2):
                left = shuffled_wires[pair_index]
                right = shuffled_wires[pair_index + 1]
                gate_name = two_qubit_gates[
                    (column_index + pair_index + seed) % len(two_qubit_gates)
                ]
                if gate_name != "swap" and (column_index + pair_index + seed) % 2 == 1:
                    left, right = right, left
                operations.append(
                    _two_qubit_operation(qubits, gate_name=gate_name, left=left, right=right)
                )
            if len(shuffled_wires) % 2 == 1:
                leftover_wire = shuffled_wires[-1]
                gate_name = "rx" if column_index % 4 == 1 else "rz"
                operations.append(
                    _single_qubit_operation(
                        qubits[leftover_wire],
                        gate_name=gate_name,
                        angle=_angle_for(rng, column_index, leftover_wire),
                    )
                )
        moments.append(Moment(operations))

    moments.append(Moment(measure(qubit, key=f"c{index}") for index, qubit in enumerate(qubits)))
    return Circuit(*moments)


def _single_qubit_operation(qubit: LineQubit, *, gate_name: str, angle: float) -> Operation:
    if gate_name == "h":
        return H(qubit)
    if gate_name == "x":
        return X(qubit)
    if gate_name == "rx":
        return rx(angle)(qubit)
    if gate_name == "ry":
        return ry(angle)(qubit)
    return rz(angle)(qubit)


def _two_qubit_operation(
    qubits: list[LineQubit],
    *,
    gate_name: str,
    left: int,
    right: int,
) -> Operation:
    if gate_name == "cx":
        return CNOT(qubits[left], qubits[right])
    if gate_name == "cz":
        return CZ(qubits[left], qubits[right])
    return SWAP(qubits[left], qubits[right])


def _angle_for(rng: Random, column_index: int, wire: int) -> float:
    base = 0.18 + (0.07 * ((column_index + wire) % 5))
    return round(base + (0.11 * (wire + 1)) + rng.uniform(0.03, 0.31), 2)


def main() -> None:
    """Render a broad Cirq circuit using only normal framework objects."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, column_count=args.columns, seed=args.seed),
            config=DrawConfig(
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved cirq-random to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a larger Cirq circuit built with normal framework operations."
    )
    parser.add_argument("--qubits", type=int, default=10, help="Number of qubits to allocate.")
    parser.add_argument(
        "--columns", type=int, default=18, help="How many random-looking columns to build."
    )
    parser.add_argument(
        "--seed", type=int, default=7, help="Seed for the deterministic pseudo-random layout."
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
