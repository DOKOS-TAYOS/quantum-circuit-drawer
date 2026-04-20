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

from quantum_circuit_drawer import (
    HistogramConfig,
    HistogramDrawStyle,
    HistogramKind,
    HistogramSort,
)


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a quasi-probability histogram payload with negative values."""

    del request
    return HistogramDemoPayload(
        data={
            "0000": 0.21,
            "0001": 0.08,
            "0011": -0.04,
            "0101": 0.15,
            "0110": 0.12,
            "1001": -0.03,
            "1100": 0.19,
            "1111": 0.32,
        },
        config=HistogramConfig(
            kind=HistogramKind.QUASI,
            sort=HistogramSort.VALUE_DESC,
            draw_style=HistogramDrawStyle.SOFT,
            show_uniform_reference=True,
            show=False,
        ),
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
