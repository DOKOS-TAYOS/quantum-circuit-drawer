"""Showcase myQLM example focused on composite structure."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from qat.lang.AQASM import CNOT, RX, H, Program, QRoutine

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import DrawConfig, OutputOptions, draw_quantum_circuit  # noqa: E402
from quantum_circuit_drawer.config import CircuitRenderOptions, DrawSideConfig  # noqa: E402

DEFAULT_FIGSIZE: tuple[float, float] = (10.6, 5.8)


def build_circuit(*, qubit_count: int, motif_count: int) -> object:
    """Build a myQLM circuit that highlights reusable composite structure."""

    program = Program()
    qbits = program.qalloc(qubit_count)
    cbits = program.calloc(qubit_count)
    routine = _build_showcase_routine()

    for start in range(motif_count):
        left = start % (qubit_count - 1)
        program.apply(routine, qbits[left], qbits[left + 1])

    H(qbits[-1])
    CNOT(qbits[0], qbits[-1])
    program.measure(list(qbits), list(cbits))
    return program.to_circ()


def _build_showcase_routine() -> QRoutine:
    routine = QRoutine()
    wires = routine.new_wires(2)
    H(wires[0])
    CNOT(wires[0], wires[1])
    RX(0.35)(wires[1])
    return routine


def main() -> None:
    """Render a myQLM circuit centered on a reusable routine."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                side=DrawSideConfig(render=CircuitRenderOptions(framework="myqlm")),
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved myqlm-structural-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a myQLM circuit that reuses one compact composite routine several times."
    )
    parser.add_argument("--qubits", type=int, default=5, help="Number of qubits to allocate.")
    parser.add_argument(
        "--motifs",
        type=int,
        default=3,
        help="How many times to apply the reusable routine across the circuit.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
