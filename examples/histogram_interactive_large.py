"""Large interactive histogram demo for quantum-circuit-drawer."""

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

from quantum_circuit_drawer import HistogramConfig, HistogramKind, HistogramMode, HistogramSort


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a 7-bit interactive counts histogram with many visible bins."""

    del request
    return HistogramDemoPayload(
        data=demo_large_counts_data(bit_width=7),
        config=HistogramConfig(
            kind=HistogramKind.COUNTS,
            mode=HistogramMode.INTERACTIVE,
            sort=HistogramSort.STATE,
            show_uniform_reference=True,
            show=False,
        ),
    )


def main() -> None:
    """Run the large interactive histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a 7-bit interactive histogram demo with slider, hover, and controls.",
        saved_label="histogram-interactive-large",
    )


if __name__ == "__main__":
    main()
