"""Configurable random-looking myQLM example for quantum-circuit-drawer."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
from random import Random

from qat.lang.AQASM import CNOT, CSIGN, RX, RY, RZ, SWAP, H, Program, X

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402


def build_circuit(*, qubit_count: int, column_count: int, seed: int) -> object:
    """Build a deterministic random-looking myQLM circuit."""

    program = Program()
    qbits = program.qalloc(qubit_count)
    cbits = program.calloc(qubit_count)
    rng = Random(seed)
    single_qubit_gates = ("h", "x", "rx", "ry", "rz")
    two_qubit_gates = ("cx", "cz", "swap")

    for column_index in range(column_count):
        if column_index % 2 == 0:
            for wire in range(qubit_count):
                gate_name = single_qubit_gates[
                    (column_index + wire + rng.randrange(len(single_qubit_gates)))
                    % len(single_qubit_gates)
                ]
                _apply_single_qubit_gate(
                    qbits=qbits,
                    gate_name=gate_name,
                    wire=wire,
                    angle=_angle_for(rng, column_index, wire),
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
                _apply_two_qubit_gate(qbits=qbits, gate_name=gate_name, left=left, right=right)
            if len(shuffled_wires) % 2 == 1:
                leftover_wire = shuffled_wires[-1]
                gate_name = "rx" if column_index % 4 == 1 else "rz"
                _apply_single_qubit_gate(
                    qbits=qbits,
                    gate_name=gate_name,
                    wire=leftover_wire,
                    angle=_angle_for(rng, column_index, leftover_wire),
                )

    program.measure(list(qbits), list(cbits))
    return program.to_circ()


def _apply_single_qubit_gate(
    *,
    qbits: object,
    gate_name: str,
    wire: int,
    angle: float,
) -> None:
    if gate_name == "h":
        H(qbits[wire])
    elif gate_name == "x":
        X(qbits[wire])
    elif gate_name == "rx":
        RX(angle)(qbits[wire])
    elif gate_name == "ry":
        RY(angle)(qbits[wire])
    elif gate_name == "rz":
        RZ(angle)(qbits[wire])


def _apply_two_qubit_gate(*, qbits: object, gate_name: str, left: int, right: int) -> None:
    if gate_name == "cx":
        CNOT(qbits[left], qbits[right])
    elif gate_name == "cz":
        CSIGN(qbits[left], qbits[right])
    else:
        SWAP(qbits[left], qbits[right])


def _angle_for(rng: Random, column_index: int, wire: int) -> float:
    base = 0.18 + (0.07 * ((column_index + wire) % 5))
    return round(base + (0.11 * (wire + 1)) + rng.uniform(0.03, 0.31), 2)


def main() -> None:
    """Render a broad myQLM circuit using only normal framework objects."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, column_count=args.columns, seed=args.seed),
            config=DrawConfig(
                output=OutputOptions(output_path=args.output, show=args.show),
            ),
        )
        if args.output is not None:
            print(f"Saved myqlm-random to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a larger myQLM circuit built with normal framework operations."
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
