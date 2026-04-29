"""OpenQASM text workflow rendered through the Qiskit parser path."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

try:
    from examples._bootstrap import ensure_local_project_on_path
    from examples._render_support import release_rendered_result
except ImportError:
    from _bootstrap import ensure_local_project_on_path
    from _render_support import release_rendered_result

ensure_local_project_on_path(__file__)

from quantum_circuit_drawer import (  # noqa: E402
    CircuitRenderOptions,
    DrawConfig,
    DrawSideConfig,
    OutputOptions,
    draw_quantum_circuit,
)

DEFAULT_FIGSIZE: tuple[float, float] = (10.6, 5.8)


def build_program(*, qubit_count: int, motif_count: int) -> str:
    """Build an OpenQASM 2 program that looks like normal handwritten input."""

    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{qubit_count}];",
        f"creg c[{qubit_count}];",
        "h q[0];",
    ]
    for index in range(qubit_count - 1):
        lines.append(f"cx q[{index}], q[{index + 1}];")
    for step in range(motif_count):
        target = step % qubit_count
        control = (target + 1) % qubit_count
        angle = 0.125 * float(step + 1)
        lines.append(f"rz({angle:.3f}) q[{target}];")
        lines.append(f"rx({angle / 2.0:.3f}) q[{control}];")
        lines.append(f"cx q[{target}], q[{control}];")
    lines.append("barrier q;")
    lines.append("measure q -> c;")
    return "\n".join(lines)


def main() -> None:
    """Render an OpenQASM text program with the public draw API."""

    args = _parse_args()
    result = None
    try:
        result = draw_quantum_circuit(
            build_program(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                side=DrawSideConfig(render=CircuitRenderOptions(framework="qasm")),
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_FIGSIZE,
                ),
            ),
        )
        if args.output is not None:
            print(f"Saved openqasm-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render OpenQASM text directly, the same way a normal script would pass it to the drawer."
    )
    parser.add_argument(
        "--qubits", type=int, default=3, help="Number of qubits in the QASM program."
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=2,
        help="Extra alternating gate motifs to append before the final measurement.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
