"""Count-ordered histogram demo for quantum-circuit-drawer."""

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

from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramDataOptions,
    HistogramKind,
    HistogramSort,
    HistogramViewOptions,
    OutputOptions,
)


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a counts histogram ordered by counts."""

    del request
    return HistogramDemoPayload(
        data=demo_counts_data(),
        config=HistogramConfig(
            data=HistogramDataOptions(kind=HistogramKind.COUNTS),
            view=HistogramViewOptions(sort=HistogramSort.VALUE_DESC),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the count-ordered histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a counts histogram ordered from highest to lowest counts.",
        saved_label="histogram-count-order",
    )


if __name__ == "__main__":
    main()
