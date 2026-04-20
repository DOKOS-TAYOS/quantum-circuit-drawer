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

from quantum_circuit_drawer import HistogramConfig, HistogramKind, HistogramSort


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a plain counts histogram payload."""

    del request
    return HistogramDemoPayload(
        data={
            "00000": 182,
            "00001": 44,
            "00011": 95,
            "00101": 61,
            "00110": 27,
            "01010": 73,
            "01100": 31,
            "01111": 118,
            "10000": 92,
            "10010": 54,
            "10101": 149,
            "10111": 43,
            "11001": 87,
            "11010": 39,
            "11100": 64,
            "11111": 176,
        },
        config=HistogramConfig(
            kind=HistogramKind.COUNTS,
            sort=HistogramSort.VALUE_DESC,
            top_k=10,
            show_uniform_reference=True,
            show=False,
        ),
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
