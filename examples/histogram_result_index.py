"""Histogram demo focused on selecting one result from a tuple payload."""

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
    """Build a histogram payload with several result entries."""

    del request
    return HistogramDemoPayload(
        data=(
            {"00": 41, "11": 39},
            {"00": 12, "01": 18, "10": 11, "11": 23},
            {"00": 5, "01": 7, "10": 8, "11": 10},
        ),
        config=HistogramConfig(
            data=HistogramDataOptions(result_index=1),
            view=HistogramViewOptions(sort="value_desc"),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the result-index histogram demo as a normal user-facing script."""

    run_histogram_example(
        build_demo,
        description="Render one selected histogram from a tuple of several results.",
        saved_label="histogram-result-index",
    )


if __name__ == "__main__":
    main()
