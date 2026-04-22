"""myQLM-result histogram demo for quantum-circuit-drawer."""

from __future__ import annotations

from qat.core import Result

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
    HistogramSort,
    HistogramViewOptions,
    OutputOptions,
)


def build_demo(request: HistogramExampleRequest) -> HistogramDemoPayload:
    """Build a histogram directly from a myQLM Result raw_data payload."""

    del request
    result = Result(nbqbits=4)
    result.add_sample(state=0b0000, probability=93)
    result.add_sample(state=0b0011, probability=128)
    result.add_sample(state=0b1010, probability=77)
    result.add_sample(state=0b1111, probability=214)
    return HistogramDemoPayload(
        data=result,
        config=HistogramConfig(
            view=HistogramViewOptions(sort=HistogramSort.VALUE_DESC),
            output=OutputOptions(show=False),
        ),
    )


def main() -> None:
    """Run the myQLM-result histogram demo."""

    run_histogram_example(
        build_demo,
        description="Render a histogram directly from a myQLM Result.raw_data payload.",
        saved_label="histogram-myqlm-result",
    )


if __name__ == "__main__":
    main()
