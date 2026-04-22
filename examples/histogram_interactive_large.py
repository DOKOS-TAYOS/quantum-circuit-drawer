"""Large histogram demo for quantum-circuit-drawer with auto interactive controls."""

from __future__ import annotations

try:
    from examples._histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        demo_large_counts_data,
        run_histogram_example,
    )
except ImportError:
    from _histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        demo_large_counts_data,
        run_histogram_example,
    )

from quantum_circuit_drawer import (
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramKind,
    HistogramSort,
    HistogramViewOptions,
    OutputOptions,
)


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a 7-bit counts histogram with conditional slider controls."""

    del request
    return HistogramDemoPayload(
        data=demo_large_counts_data(bit_width=7),
        config=HistogramConfig(
            data=HistogramDataOptions(kind=HistogramKind.COUNTS),
            view=HistogramViewOptions(sort=HistogramSort.STATE),
            appearance=HistogramAppearanceOptions(show_uniform_reference=True),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the large histogram demo."""

    run_histogram_example(
        build_demo,
        description=(
            "Render a 7-bit histogram demo with auto controls, a conditional slider button, "
            "and multiline marginal help."
        ),
        saved_label="histogram-interactive-large",
    )


if __name__ == "__main__":
    main()
