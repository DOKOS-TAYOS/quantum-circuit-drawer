"""Histogram demo focused on top-k ordering and filtering."""

from __future__ import annotations

try:
    from examples._histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        parse_histogram_example_args,
    )
except ImportError:
    from _histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        parse_histogram_example_args,
    )

from quantum_circuit_drawer import HistogramConfig, plot_histogram


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a histogram payload that makes top-k filtering easy to see."""

    del request
    return HistogramDemoPayload(
        data={
            "0000": 14,
            "0001": 5,
            "0010": 21,
            "0011": 7,
            "0100": 17,
            "0101": 3,
            "0110": 26,
            "0111": 11,
            "1000": 31,
            "1001": 9,
            "1010": 28,
            "1011": 4,
            "1100": 22,
            "1101": 8,
            "1110": 18,
            "1111": 35,
        },
        config=HistogramConfig(
            sort="value_desc",
            top_k=5,
            show=False,
        ),
    )


def main() -> None:
    """Run the top-k histogram demo as a normal user-facing script."""

    request = parse_histogram_example_args(
        description="Render a histogram demo focused on top-k ordering.",
    )
    payload = build_demo(request)
    base_config = payload.config
    config = HistogramConfig(
        kind=base_config.kind,
        mode=base_config.mode if request.mode is None else request.mode,
        sort=base_config.sort if request.sort is None else request.sort,
        top_k=base_config.top_k if request.top_k is None else request.top_k,
        qubits=base_config.qubits if request.qubits is None else request.qubits,
        result_index=base_config.result_index
        if request.result_index is None
        else request.result_index,
        data_key=base_config.data_key if request.data_key is None else request.data_key,
        preset=base_config.preset if request.preset is None else request.preset,
        theme=base_config.theme if request.theme is None else request.theme,
        draw_style=base_config.draw_style if request.draw_style is None else request.draw_style,
        state_label_mode=(
            base_config.state_label_mode
            if request.state_label_mode is None
            else request.state_label_mode
        ),
        hover=base_config.hover if request.hover is None else request.hover,
        show_uniform_reference=(
            base_config.show_uniform_reference
            if request.show_uniform_reference is None
            else request.show_uniform_reference
        ),
        output_path=request.output,
        show=request.show,
        figsize=request.figsize,
    )
    result = plot_histogram(payload.data, config=config)
    if hasattr(result.figure, "set_label"):
        result.figure.set_label("histogram-top-k")
    if request.output is not None:
        print(f"Saved histogram-top-k to {request.output}")


if __name__ == "__main__":
    main()
