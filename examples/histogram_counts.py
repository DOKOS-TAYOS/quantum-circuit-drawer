"""Counts histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

try:
    from examples._histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        run_histogram_example,
    )
except ImportError:
    from _histogram_shared import (
        HistogramDemoPayload,
        HistogramExampleRequest,
        run_histogram_example,
    )

from quantum_circuit_drawer import HistogramConfig, HistogramKind


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a plain counts histogram payload."""

    del request
    return HistogramDemoPayload(
        data={"00": 51, "01": 12, "10": 7, "11": 58},
        config=HistogramConfig(kind=HistogramKind.COUNTS, show=False),
    )


def main() -> None:
    """Run the counts histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a counts histogram demo.",
        saved_label="histogram-counts",
    )


if __name__ == "__main__":
    main()
