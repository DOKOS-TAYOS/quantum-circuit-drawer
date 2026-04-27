"""Show diagnostics and metadata returned by public result objects."""

from __future__ import annotations

try:
    from examples._render_support import release_rendered_result
    from examples._shared import ExampleRequest, build_draw_config, parse_example_args
except ImportError:
    from _render_support import release_rendered_result
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import (
    CircuitBuilder,
    analyze_quantum_circuit,
    draw_quantum_circuit,
)


def build_circuit(request: ExampleRequest) -> object:
    """Build a circuit that naturally produces useful public metadata."""

    qubit_count = max(5, request.qubits)
    builder = CircuitBuilder(qubit_count, qubit_count, name="diagnostics_showcase")
    builder.h(0).cx(0, 1).barrier(0, 1, 2)
    for step in range(max(2, request.columns)):
        target = step % qubit_count
        partner = (target + 1) % qubit_count
        builder.rx(0.15 * float(step + 1), target)
        builder.cz(target, partner)
    builder.measure_all()
    return builder.build()


def main() -> None:
    """Run the diagnostics showcase."""

    request = parse_example_args(
        description="Render and print public diagnostics and metadata.",
        default_qubits=5,
        default_columns=6,
        columns_help="Diagnostic motifs to append before measurement",
        default_mode="auto",
    )
    circuit = build_circuit(request)
    config = build_draw_config(request, framework="ir")
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
        if request.output is not None:
            print(f"Saved diagnostics-showcase to {request.output}")
    finally:
        if result is not None:
            release_rendered_result(result)


if __name__ == "__main__":
    main()
