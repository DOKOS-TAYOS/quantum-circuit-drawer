"""Show common public API utilities, exports, and result helpers."""

from __future__ import annotations

from pathlib import Path

try:
    from examples._render_support import release_rendered_result
    from examples._shared import ExampleRequest, build_draw_config, parse_example_args
except ImportError:
    from _render_support import release_rendered_result
    from _shared import ExampleRequest, build_draw_config, parse_example_args

from quantum_circuit_drawer import (
    CircuitBuilder,
    HistogramConfig,
    HistogramDataOptions,
    HistogramMode,
    HistogramViewOptions,
    OutputOptions,
    analyze_quantum_circuit,
    draw_quantum_circuit,
    plot_histogram,
)


def build_circuit(request: ExampleRequest) -> object:
    """Build a framework-free circuit for public API utility examples."""

    qubit_count = max(3, request.qubits)
    builder = CircuitBuilder(qubit_count, qubit_count, name="public_api_utilities")
    builder.h(0).cx(0, 1).ry(0.45, 2)
    for step in range(max(1, request.columns)):
        target = step % qubit_count
        partner = (target + 1) % qubit_count
        builder.rz(0.18 * float(step + 1), target)
        builder.cx(target, partner)
    builder.barrier().measure_all()
    return builder.build()


def demo_counts() -> dict[str, int]:
    """Return counts used by the result-helper part of the showcase."""

    return {
        "000": 31,
        "001": 8,
        "010": 15,
        "011": 44,
        "100": 22,
        "101": 6,
        "110": 18,
        "111": 49,
    }


def main() -> None:
    """Run the public API utility showcase as a normal user-facing script."""

    request = parse_example_args(
        description="Render a circuit, analyze it, export pages, and write histogram data.",
        default_qubits=4,
        default_columns=4,
        columns_help="Public API motifs to append before the measurements",
        default_mode="pages",
    )
    circuit = build_circuit(request)
    analysis = analyze_quantum_circuit(circuit, config=build_draw_config(request, framework="ir"))
    result = None
    histogram_result = None
    try:
        result = draw_quantum_circuit(
            circuit,
            config=build_draw_config(request, framework="ir"),
        )
        histogram_result = plot_histogram(
            demo_counts(),
            config=HistogramConfig(
                data=HistogramDataOptions(top_k=6),
                view=HistogramViewOptions(mode=HistogramMode.STATIC, sort="value_desc"),
                output=OutputOptions(show=False, figsize=(7.2, 4.0)),
            ),
        )
        _save_related_outputs(
            output_path=request.output,
            draw_result=result,
            histogram_result=histogram_result,
        )
        if request.output is not None:
            print(f"Saved public-api-utilities-showcase to {request.output}")
        print(
            "Analysis: "
            f"{analysis.quantum_wire_count} qubits, "
            f"{analysis.operation_count} operations, "
            f"{analysis.page_count} page(s)"
        )
    finally:
        if result is not None:
            release_rendered_result(result)
        if histogram_result is not None:
            release_rendered_result(histogram_result)


def _save_related_outputs(
    *,
    output_path: Path | None,
    draw_result: object,
    histogram_result: object,
) -> None:
    if output_path is None:
        return

    pages_dir = output_path.with_name(f"{output_path.stem}_pages")
    draw_result.save_all_pages(pages_dir, filename_prefix=output_path.stem)
    histogram_path = output_path.with_name(f"{output_path.stem}_histogram{output_path.suffix}")
    histogram_csv_path = output_path.with_name(f"{output_path.stem}_histogram.csv")
    histogram_result.save(histogram_path)
    histogram_result.to_csv(histogram_csv_path)
    print(f"Saved page exports to {pages_dir}")
    print(f"Saved histogram CSV to {histogram_csv_path}")


if __name__ == "__main__":
    main()
