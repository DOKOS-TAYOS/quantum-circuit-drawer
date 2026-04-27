"""Show accessible style presets for circuit and histogram output."""

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


def build_circuit(request: ExampleRequest) -> object:
    """Build a compact circuit with varied gate shapes for the accessible preset."""

    qubit_count = max(4, request.qubits)
    builder = CircuitBuilder(qubit_count, qubit_count, name="style_accessible")
    builder.h(0).cx(0, 1).rz(0.4, 2).swap(2, 3)
    for step in range(max(1, request.columns)):
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
    """Run the accessible style showcase."""

    request = parse_example_args(
        description="Render accessible circuit and histogram styling.",
        default_qubits=5,
        default_columns=3,
        columns_help="Accessible style motifs to append before measurement",
    )
    styled_request = _with_accessible_preset(request)
    circuit_result = None
    histogram_result = None
    try:
        circuit_result = draw_quantum_circuit(
            build_circuit(styled_request),
            config=build_draw_config(styled_request, framework="ir"),
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
        _save_companion_histogram(request.output, histogram_result)
        if request.output is not None:
            print(f"Saved style-accessible-showcase to {request.output}")
    finally:
        if circuit_result is not None:
            release_rendered_result(circuit_result)
        if histogram_result is not None:
            release_rendered_result(histogram_result)


def _with_accessible_preset(request: ExampleRequest) -> ExampleRequest:
    return ExampleRequest(
        qubits=request.qubits,
        columns=request.columns,
        mode=request.mode,
        view=request.view,
        topology=request.topology,
        seed=request.seed,
        output=request.output,
        show=request.show,
        figsize=request.figsize,
        hover=request.hover,
        hover_matrix=request.hover_matrix,
        hover_matrix_max_qubits=request.hover_matrix_max_qubits,
        hover_show_size=request.hover_show_size,
        preset="accessible",
        composite_mode=request.composite_mode,
        unsupported_policy=request.unsupported_policy,
    )


def _save_companion_histogram(output_path: Path | None, histogram_result: object) -> None:
    if output_path is None:
        return
    histogram_path = output_path.with_name(f"{output_path.stem}_histogram{output_path.suffix}")
    histogram_result.save(histogram_path)


if __name__ == "__main__":
    main()
