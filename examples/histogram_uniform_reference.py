"""Uniform-reference histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

try:
    from examples._histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        demo_counts_data,
        run_histogram_example,
    )
except ImportError:
    from _histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        demo_counts_data,
        run_histogram_example,
    )

from quantum_circuit_drawer import HistogramConfig, HistogramDrawStyle, HistogramKind


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a counts histogram with the uniform reference guide."""

    del request
    return HistogramDemoPayload(
        data=demo_counts_data(),
        config=HistogramConfig(
            kind=HistogramKind.COUNTS,
            draw_style=HistogramDrawStyle.OUTLINE,
            show_uniform_reference=True,
            show=False,
        ),
    )


def main() -> None:
    """Run the uniform-reference histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a counts histogram with the uniform reference line.",
        saved_label="histogram-uniform-reference",
    )


if __name__ == "__main__":
    main()
