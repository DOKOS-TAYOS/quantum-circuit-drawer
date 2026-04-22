"""Multi-register histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

try:
    from examples._histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        demo_multi_register_counts_data,
        run_histogram_example,
    )
except ImportError:
    from _histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        demo_multi_register_counts_data,
        run_histogram_example,
    )

from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramDataOptions,
    HistogramKind,
    HistogramSort,
    HistogramStateLabelMode,
    HistogramViewOptions,
    OutputOptions,
)


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a counts histogram that uses several space-separated registers."""

    del request
    return HistogramDemoPayload(
        data=demo_multi_register_counts_data(),
        config=HistogramConfig(
            data=HistogramDataOptions(kind=HistogramKind.COUNTS),
            view=HistogramViewOptions(
                sort=HistogramSort.STATE,
                state_label_mode=HistogramStateLabelMode.DECIMAL,
            ),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the multi-register histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a counts histogram with several registers and decimal labels per register.",
        saved_label="histogram-multi-register",
    )


if __name__ == "__main__":
    main()
