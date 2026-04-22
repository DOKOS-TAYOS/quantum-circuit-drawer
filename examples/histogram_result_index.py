"""Histogram demo focused on selecting one result from a tuple payload."""

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
    """Build a histogram payload with several result entries."""

    del request
    return HistogramDemoPayload(
        data=(
            {"00": 41, "11": 39},
            {"00": 12, "01": 18, "10": 11, "11": 23},
            {"00": 5, "01": 7, "10": 8, "11": 10},
        ),
        config=HistogramConfig(
            result_index=1,
            sort="value_desc",
            show=False,
        ),
    )


def main() -> None:
    """Run the result-index histogram demo as a normal user-facing script."""

    request = parse_histogram_example_args(
        description="Render one selected histogram from a tuple of several results.",
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
        result.figure.set_label("histogram-result-index")
    if request.output is not None:
        print(f"Saved histogram-result-index to {request.output}")


if __name__ == "__main__":
    main()
