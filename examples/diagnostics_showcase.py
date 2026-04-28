"""Show diagnostics and metadata returned by public result objects."""

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
    CircuitBuilder,
    DrawConfig,
    OutputOptions,
    analyze_quantum_circuit,
    draw_quantum_circuit,
)

DEFAULT_FIGSIZE: tuple[float, float] = (8.8, 4.8)


def build_circuit(*, qubit_count: int, motif_count: int) -> object:
    """Build a circuit that naturally produces useful public metadata."""

    builder = CircuitBuilder(qubit_count, qubit_count, name="diagnostics_showcase")
    builder.h(0).cx(0, 1).barrier(0, 1, 2)
    for step in range(motif_count):
        target = step % qubit_count
        partner = (target + 1) % qubit_count
        builder.rx(0.15 * float(step + 1), target)
        builder.cz(target, partner)
    builder.measure_all()
    return builder.build()


def main() -> None:
    """Render a circuit and print useful diagnostics and metadata."""

    args = _parse_args()
    circuit = build_circuit(qubit_count=args.qubits, motif_count=args.motifs)
    config = DrawConfig(
        output=OutputOptions(
            output_path=args.output,
            show=args.show,
            figsize=DEFAULT_FIGSIZE,
        )
    )
    analysis = analyze_quantum_circuit(circuit, config=config)
    result = None
    try:
        result = draw_quantum_circuit(circuit, config=config)
        result_summary = result.to_dict()
        print(
            "Diagnostics: "
            f"mode={result_summary['mode']}, "
            f"pages={result_summary['page_count']}, "
            f"warnings={len(result.warnings)}"
        )
        print(
            "Analysis: "
            f"layers={analysis.layer_count}, "
            f"operations={analysis.operation_count}, "
            f"multi_qubit={analysis.multi_qubit_operation_count}"
        )
        if args.output is not None:
            print(f"Saved diagnostics-showcase to {args.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render a circuit and print diagnostics from the result objects."
    )
    parser.add_argument(
        "--qubits", type=int, default=5, help="Number of qubits in the demo circuit."
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=6,
        help="Extra motifs to append before the final measurements.",
    )
    parser.add_argument("--output", type=Path, help="Optional output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
