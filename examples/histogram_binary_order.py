"""Binary-order histogram demo for quantum-circuit-drawer."""

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

from quantum_circuit_drawer import HistogramConfig, HistogramKind, HistogramSort


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a counts histogram ordered by binary state labels."""

    del request
    return HistogramDemoPayload(
        data=demo_counts_data(),
        config=HistogramConfig(
            kind=HistogramKind.COUNTS,
            sort=HistogramSort.STATE,
            show=False,
        ),
    )


def main() -> None:
    """Run the binary-order histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a counts histogram ordered by binary state labels.",
        saved_label="histogram-binary-order",
    )


if __name__ == "__main__":
    main()
