"""Show common public API utilities, exports, and result helpers."""

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
    CircuitRenderOptions,
    DrawConfig,
    DrawMode,
    DrawResult,
    DrawSideConfig,
    HistogramConfig,
    HistogramDataOptions,
    HistogramMode,
    HistogramResult,
    HistogramSort,
    HistogramViewOptions,
    LatexBackend,
    OutputOptions,
    analyze_quantum_circuit,
    circuit_to_latex,
    draw_quantum_circuit,
    plot_histogram,
)

DEFAULT_CIRCUIT_FIGSIZE: tuple[float, float] = (10.6, 5.8)


def build_circuit(*, qubit_count: int, motif_count: int) -> object:
    """Build a framework-free circuit for public API utility examples."""

    builder = CircuitBuilder(qubit_count, qubit_count, name="public_api_utilities")
    builder.h(0).cx(0, 1).ry(0.45, 2)
    for step in range(motif_count):
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
    """Render a circuit, analyze it, and export companion artifacts."""

    args = _parse_args()
    circuit = build_circuit(qubit_count=args.qubits, motif_count=args.motifs)
    draw_config = DrawConfig(
        side=DrawSideConfig(render=CircuitRenderOptions(mode=DrawMode.PAGES)),
        output=OutputOptions(
            output_path=args.output,
            show=args.show,
            figsize=DEFAULT_CIRCUIT_FIGSIZE,
        ),
    )
    analysis = analyze_quantum_circuit(circuit, config=draw_config)
    latex_result = circuit_to_latex(
        circuit,
        config=draw_config,
        backend=LatexBackend.QUANTIKZ,
        mode=DrawMode.PAGES,
    )
    result = None
    histogram_result = None
    try:
        result = draw_quantum_circuit(circuit, config=draw_config)
        histogram_result = plot_histogram(
            demo_counts(),
            config=HistogramConfig(
                data=HistogramDataOptions(top_k=6),
                view=HistogramViewOptions(
                    mode=HistogramMode.STATIC,
                    sort=HistogramSort.VALUE_DESC,
                ),
                output=OutputOptions(show=False, figsize=(8.6, 4.8)),
            ),
        )
        _save_related_outputs(
            output_path=args.output,
            draw_result=result,
            histogram_result=histogram_result,
            latex_source=latex_result.source,
        )
        if args.output is not None:
            print(f"Saved public-api-utilities-showcase to {args.output}")
        print(
            "Analysis: "
            f"{analysis.quantum_wire_count} qubits, "
            f"{analysis.operation_count} operations, "
            f"{analysis.page_count} page(s), "
            f"{latex_result.page_count} LaTeX page(s)"
        )
    finally:
        if result is not None:
            release_rendered_result(result)
        if histogram_result is not None:
            release_rendered_result(histogram_result)


def _save_related_outputs(
    *,
    output_path: Path | None,
    draw_result: DrawResult,
    histogram_result: HistogramResult,
    latex_source: str,
) -> None:
    if output_path is None:
        return

    pages_dir = output_path.with_name(f"{output_path.stem}_pages")
    draw_result.save_all_pages(pages_dir, filename_prefix=output_path.stem)
    histogram_path = output_path.with_name(f"{output_path.stem}_histogram{output_path.suffix}")
    histogram_csv_path = output_path.with_name(f"{output_path.stem}_histogram.csv")
    latex_path = output_path.with_name(f"{output_path.stem}_quantikz.tex")
    histogram_result.save(histogram_path)
    histogram_result.to_csv(histogram_csv_path)
    latex_path.write_text(latex_source, encoding="utf-8")
    print(f"Saved page exports to {pages_dir}")
    print(f"Saved histogram CSV to {histogram_csv_path}")
    print(f"Saved LaTeX snippet to {latex_path}")


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Show analysis, result helpers, page exports, and histogram CSV export."
    )
    parser.add_argument(
        "--qubits", type=int, default=4, help="Number of qubits in the demo circuit."
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=4,
        help="Extra circuit motifs to append before the final measurements.",
    )
    parser.add_argument("--output", type=Path, help="Optional base output image path.")
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
