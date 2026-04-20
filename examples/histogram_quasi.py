"""Quasi-probability histogram demo for quantum-circuit-drawer."""

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
    """Build a quasi-probability histogram payload with negative values."""

    del request
    return HistogramDemoPayload(
        data={"00": 0.52, "01": -0.08, "10": 0.21, "11": 0.35},
        config=HistogramConfig(kind=HistogramKind.QUASI, show=False),
    )


def main() -> None:
    """Run the quasi-probability histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a quasi-probability histogram demo.",
        saved_label="histogram-quasi",
    )


if __name__ == "__main__":
    main()
