"""Non-negative quasi-probability histogram demo for quantum-circuit-drawer."""

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
    HistogramAppearanceOptions,
    HistogramConfig,
    HistogramDataOptions,
    HistogramDrawStyle,
    HistogramKind,
    OutputOptions,
)


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a quasi-probability histogram payload with only non-negative values."""

    del request
    return HistogramDemoPayload(
        data={
            "0000": 0.11,
            "0001": 0.07,
            "0011": 0.06,
            "0101": 0.13,
            "0110": 0.09,
            "1001": 0.08,
            "1100": 0.17,
            "1111": 0.29,
        },
        config=HistogramConfig(
            data=HistogramDataOptions(kind=HistogramKind.QUASI),
            appearance=HistogramAppearanceOptions(
                theme="paper",
                draw_style=HistogramDrawStyle.SOFT,
            ),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the non-negative quasi-probability histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a quasi-probability histogram demo without negative bars.",
        saved_label="histogram-quasi-nonnegative",
    )


if __name__ == "__main__":
    main()
