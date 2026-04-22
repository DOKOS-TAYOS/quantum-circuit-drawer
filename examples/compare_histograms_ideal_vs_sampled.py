"""Compare ideal and sampled histogram workflows with the public compare API."""

from __future__ import annotations

try:
    from examples._compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        run_compare_example,
    )
except ImportError:
    from _compare_shared import (
        CompareDemoPayload,
        CompareExampleRequest,
        run_compare_example,
    )

from quantum_circuit_drawer import (
    HistogramCompareConfig,
    HistogramCompareOptions,
    OutputOptions,
)


def build_demo(request: CompareExampleRequest) -> CompareDemoPayload:
    """Build a compare payload for ideal versus sampled histogram data."""

    del request
    return CompareDemoPayload(
        compare_kind="histograms",
        left_data={
            "000": 0.125,
            "001": 0.125,
            "010": 0.125,
            "011": 0.125,
            "100": 0.125,
            "101": 0.125,
            "110": 0.125,
            "111": 0.125,
        },
        right_data={
            "000": 17,
            "001": 13,
            "010": 9,
            "011": 18,
            "100": 12,
            "101": 10,
            "110": 15,
            "111": 14,
        },
        config=HistogramCompareConfig(
            compare=HistogramCompareOptions(
                left_label="Ideal",
                right_label="Sampled",
                sort="delta_desc",
            ),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the histogram compare demo as a normal user-facing script."""

    run_compare_example(
        build_demo,
        description="Compare an ideal distribution against sampled counts.",
        saved_label="compare-histograms-ideal-vs-sampled",
    )


if __name__ == "__main__":
    main()
