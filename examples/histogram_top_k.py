"""Histogram demo focused on top-k ordering and filtering."""

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

from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramDataOptions,
    HistogramViewOptions,
    OutputOptions,
)


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
            data=HistogramDataOptions(top_k=5),
            view=HistogramViewOptions(sort="value_desc"),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the top-k histogram demo as a normal user-facing script."""

    run_histogram_example(
        build_demo,
        description="Render a histogram demo focused on top-k ordering.",
        saved_label="histogram-top-k",
    )


if __name__ == "__main__":
    main()
