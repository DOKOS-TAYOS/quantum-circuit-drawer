"""Compare several probability distributions in one overlay histogram."""

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
from quantum_circuit_drawer.histogram import HistogramDataOptions


def build_demo(request: CompareExampleRequest) -> CompareDemoPayload:
    """Build a multi-series histogram comparison payload."""

    del request
    ideal = {
        "000": 0.48,
        "001": 0.01,
        "010": 0.01,
        "011": 0.0,
        "100": 0.0,
        "101": 0.01,
        "110": 0.01,
        "111": 0.48,
    }
    noisy_simulator = {
        "000": 0.42,
        "001": 0.05,
        "010": 0.03,
        "011": 0.02,
        "100": 0.02,
        "101": 0.03,
        "110": 0.05,
        "111": 0.38,
    }
    hardware_raw = {
        "000": 0.35,
        "001": 0.08,
        "010": 0.06,
        "011": 0.04,
        "100": 0.05,
        "101": 0.06,
        "110": 0.09,
        "111": 0.27,
    }
    mitigated = {
        "000": 0.44,
        "001": 0.03,
        "010": 0.02,
        "011": 0.01,
        "100": 0.01,
        "101": 0.02,
        "110": 0.04,
        "111": 0.43,
    }
    return CompareDemoPayload(
        compare_kind="histograms",
        left_data=ideal,
        right_data=noisy_simulator,
        extra_data=(hardware_raw, mitigated),
        config=HistogramCompareConfig(
            data=HistogramDataOptions(top_k=8),
            compare=HistogramCompareOptions(
                series_labels=("Ideal", "Noisy sim", "Hardware raw", "Mitigated"),
                sort="delta_desc",
            ),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the multi-series histogram compare demo as a normal script."""

    run_compare_example(
        build_demo,
        description="Compare ideal, noisy, raw hardware, and mitigated distributions.",
        saved_label="compare-histograms-multi-series",
    )


if __name__ == "__main__":
    main()
