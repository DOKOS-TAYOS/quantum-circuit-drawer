"""Show accessible style presets for circuit and histogram output."""

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
    CircuitAppearanceOptions,
    CircuitBuilder,
    DrawConfig,
    DrawSideConfig,
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDrawStyle,
    HistogramMode,
    HistogramViewOptions,
    OutputOptions,
    StylePreset,
    draw_quantum_circuit,
    plot_histogram,
)

DEFAULT_CIRCUIT_FIGSIZE: tuple[float, float] = (8.8, 4.8)


def build_circuit(*, qubit_count: int, motif_count: int) -> object:
    """Build a compact circuit with varied gate shapes for the accessible preset."""

    builder = CircuitBuilder(qubit_count, qubit_count, name="style_accessible")
    builder.h(0).cx(0, 1).rz(0.4, 2).swap(2, 3)
    for step in range(motif_count):
        target = step % qubit_count
        partner = (target + 2) % qubit_count
        builder.ry(0.22 * float(step + 1), target)
        builder.cz(target, partner)
    builder.measure_all()
    return builder.build()


def demo_counts() -> dict[str, int]:
    """Return counts used for the accessible histogram companion image."""

    return {
        "0000": 12,
        "0001": 31,
        "0010": 7,
        "0011": 46,
        "0100": 16,
        "0101": 25,
        "0110": 4,
        "0111": 39,
    }


def main() -> None:
    """Render accessible circuit and histogram styling side by side in spirit."""

    args = _parse_args()
    circuit_result = None
    histogram_result = None
    try:
        circuit_result = draw_quantum_circuit(
            build_circuit(qubit_count=args.qubits, motif_count=args.motifs),
            config=DrawConfig(
                side=DrawSideConfig(
                    appearance=CircuitAppearanceOptions(preset=StylePreset.ACCESSIBLE),
                ),
                output=OutputOptions(
                    output_path=args.output,
                    show=args.show,
                    figsize=DEFAULT_CIRCUIT_FIGSIZE,
                ),
            ),
        )
        histogram_result = plot_histogram(
            demo_counts(),
            config=HistogramConfig(
                view=HistogramViewOptions(mode=HistogramMode.STATIC, sort="value_desc"),
                appearance=HistogramAppearanceOptions(
                    preset=StylePreset.ACCESSIBLE,
                    draw_style=HistogramDrawStyle.OUTLINE,
                    show_uniform_reference=True,
                ),
                output=OutputOptions(show=False, figsize=(8.4, 4.6)),
            ),
        )
        _save_companion_histogram(args.output, histogram_result)
        if args.output is not None:
            print(f"Saved style-accessible-showcase to {args.output}")
    finally:
        if circuit_result is not None:
            release_rendered_result(circuit_result)
        if histogram_result is not None:
            release_rendered_result(histogram_result)


def _save_companion_histogram(output_path: Path | None, histogram_result: object) -> None:
    if output_path is None:
        return
    histogram_path = output_path.with_name(f"{output_path.stem}_histogram{output_path.suffix}")
    histogram_result.save(histogram_path)


def _parse_args() -> Namespace:
    parser = ArgumentParser(
        description="Render the accessible preset on both a circuit and a histogram."
    )
    parser.add_argument(
        "--qubits", type=int, default=5, help="Number of qubits in the demo circuit."
    )
    parser.add_argument(
        "--motifs",
        type=int,
        default=3,
        help="Extra motifs to append before the final measurements.",
    )
    parser.add_argument(
        "--output", type=Path, help="Optional output image path for the circuit render."
    )
    parser.add_argument("--show", dest="show", action="store_true", default=True)
    parser.add_argument("--no-show", dest="show", action="store_false")
    return parser.parse_args()


if __name__ == "__main__":
    main()
